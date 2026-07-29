"""摄取 Worker —— Dramatiq 异步任务。

完整摄取链路：
1. 从 PostgreSQL 读取 Document 记录
2. 从 MinIO 下载原始文件
3. MIME 检测 → ParserRegistry 获取解析器
4. 解析 → 标准化 Block → 结构化分块
5. BGE-M3 Embedding → Qdrant 写入
6. 更新 Document 状态（ready / error）
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory

import dramatiq
import structlog
from dramatiq.brokers.redis import RedisBroker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import joinedload

from packages.core.config.settings import settings
from packages.core.exceptions import UnsupportedFormat
from packages.core.models.block import BlockType
from packages.core.models.document import Document, DocumentStatus, DocumentVersion
from packages.core.models.index_profile import IndexProfile
from packages.parsers import registry as parser_registry
from packages.parsers.chunker import chunk_document
from packages.providers.bge.embedding import BGEM3Embedding
from packages.retrieval.hybrid import QdrantHybridRetriever

logger = structlog.get_logger()

# ─── Broker ───
redis_broker = RedisBroker(url=settings.redis_url)
dramatiq.set_broker(redis_broker)

# ─── 全局组件（懒加载） ───
_embedder: BGEM3Embedding | None = None
_retriever: QdrantHybridRetriever | None = None
_minio_client: "MinioClient | None" = None


def _get_embedder() -> BGEM3Embedding:
    global _embedder
    if _embedder is None:
        from packages.providers.bge.embedding import BGEM3Embedding
        _embedder = BGEM3Embedding(
            model_path=settings.bge_model_path,
            device="cpu",
        )
    return _embedder


def _get_retriever() -> QdrantHybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = QdrantHybridRetriever(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key or None,
        )
    return _retriever


def _get_minio():
    """获取 MinIO 客户端（无需 API 应用依赖）。"""
    from minio import Minio

    global _minio_client
    if _minio_client is None:
        _minio_client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    return _minio_client


def _get_db_engine():
    return create_async_engine(settings.database_url)


# ─── 任务定义 ───


@dramatiq.actor(
    max_retries=3,
    min_backoff=2000,
    max_backoff=60000,
    time_limit=600000,  # 10 min
)
def ingest_document(document_id: str) -> None:
    """异步摄取任务入口。"""
    import asyncio
    asyncio.run(_ingest_document_async(document_id))


@dramatiq.actor(max_retries=2, time_limit=300000)
def reindex_document(document_id: str) -> None:
    """重新索引文档。"""
    import asyncio
    asyncio.run(_reindex_document_async(document_id))


@dramatiq.actor(max_retries=1)
def delete_document_vectors(document_id: str, kb_id: str) -> None:
    """删除文档向量。"""
    import asyncio
    asyncio.run(_delete_vectors_async(document_id, kb_id))


# ─── 核心摄取逻辑 ───


async def _ingest_document_async(document_id: str) -> None:
    """异步摄取主流程。"""
    logger.info("Starting document ingestion", document_id=document_id)

    engine = _get_db_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession)

    async with session_maker() as db:
        try:
            # 1. 读取文档记录
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()
            if not doc:
                logger.error("Document not found", document_id=document_id)
                return

            # 标记 parsing
            doc.status = DocumentStatus.PARSING
            await db.flush()

            # 2. 从 MinIO 下载
            minio_client = _get_minio()
            with TemporaryDirectory() as tmpdir:
                local_path = Path(tmpdir) / doc.filename
                minio_client.fget_object(
                    bucket_name=settings.minio_bucket,
                    object_name=doc.storage_path,
                    file_path=str(local_path),
                )

                # 3. 解析
                blocks = await parser_registry.parse(
                    str(local_path), filename=doc.filename
                )

                if not blocks:
                    raise ValueError("Parser returned no blocks")

                # 4. 分块
                chunks = chunk_document(
                    blocks,
                    document_id=str(doc.id),
                    kb_id=str(doc.kb_id),
                    chunk_size=512,
                )

                if not chunks:
                    raise ValueError("Chunker returned no chunks")

                # 5. 创建版本记录
                file_hash = hashlib.sha256(
                    Path(local_path).read_bytes()
                ).hexdigest()

                version = DocumentVersion(
                    document_id=doc.id,
                    version=doc.current_version + 1,
                    file_hash=file_hash,
                    file_size=doc.file_size,
                    parser_version=doc.parser_version or "1.0",
                    chunk_count=len(chunks),
                )
                db.add(version)
                await db.flush()

                # 6. Embedding + 写入 Qdrant
                embedder = _get_embedder()
                retriever = _get_retriever()

                texts = [c.text for c in chunks]
                if not texts:
                    raise ValueError("No text to embed")

                dense_vectors, _ = await embedder.embed_documents(texts)

                # 确保 Qdrant 集合存在
                collection_name = f"kb_{str(doc.kb_id).replace('-', '_')}"
                retriever.ensure_collection(
                    collection_name=collection_name,
                    dense_dim=embedder.dimension(),
                )

                # 构建 Qdrant payload
                from qdrant_client import models as qdrant_models

                points = []
                for i, (chunk, dense) in enumerate(zip(chunks, dense_vectors)):
                    point_id = str(uuid.uuid4())
                    payload = {
                        "chunk_id": point_id,
                        "document_id": str(doc.id),
                        "kb_id": str(doc.kb_id),
                        "file_name": doc.filename,
                        "text": chunk.text,
                        "page_number": chunk.page_number,
                        "heading_path": chunk.heading_path,
                        "block_type": chunk.block_type,
                        "token_count": chunk.token_count,
                    }
                    points.append(qdrant_models.PointStruct(
                        id=point_id,
                        vector={"dense": dense},
                        payload=payload,
                    ))

                    chunks[i].content_hash = point_id

                if points:
                    retriever.insert_batch(collection_name, points)

                # 7. 更新索引签名
                existing = await db.execute(
                    select(IndexProfile).where(
                        IndexProfile.kb_id == doc.kb_id
                    )
                )
                profile = existing.scalar_one_or_none()
                if not profile:
                    profile = IndexProfile(
                        kb_id=doc.kb_id,
                        embedding_provider="bge-m3",
                        model_name="BAAI/bge-m3",
                        dimension=embedder.dimension(),
                        distance_metric="cosine",
                        chunk_strategy="structure_aware",
                        chunk_size=512,
                        chunk_overlap=64,
                    )
                    db.add(profile)

                # 8. 更新文档状态
                doc.status = DocumentStatus.READY
                doc.current_version = version.version
                doc.parser_version = version.parser_version

                await db.flush()

                logger.info(
                    "Document ingestion complete",
                    document_id=document_id,
                    blocks=len(blocks),
                    chunks=len(chunks),
                )

        except UnsupportedFormat as e:
            await _mark_error(db, document_id, f"Unsupported format: {e}")
        except Exception as e:
            await _mark_error(db, document_id, str(e)[:1000])
            logger.exception("Ingestion failed", document_id=document_id, error=str(e))
        finally:
            await engine.dispose()


async def _mark_error(
    db: AsyncSession, document_id: str, error: str
) -> None:
    """标记文档为错误状态。"""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if doc:
        doc.status = DocumentStatus.ERROR
        doc.error_message = error
        await db.flush()


async def _reindex_document_async(document_id: str) -> None:
    """重新索引文档。"""
    engine = _get_db_engine()
    session_maker = async_sessionmaker(engine, class_=AsyncSession)
    async with session_maker() as db:
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if doc:
            await _delete_vectors_async(document_id, str(doc.kb_id))
    await engine.dispose()

    await _ingest_document_async(document_id)


async def _delete_vectors_async(document_id: str, kb_id: str) -> None:
    """删除向量索引。"""
    retriever = _get_retriever()
    collection_name = f"kb_{kb_id.replace('-', '_')}"
    try:
        retriever.delete_by_document(collection_name, document_id)
        logger.info("Vectors deleted", document_id=document_id)
    except Exception as e:
        logger.warning("Vector deletion failed", error=str(e))
