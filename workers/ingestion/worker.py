"""DeepDocs 摄取 Worker —— 基于 Dramatiq 的异步任务消费。"""

from __future__ import annotations

import dramatiq
from dramatiq.brokers.redis import RedisBroker

from packages.core.config.settings import settings

# ─── Broker ───
redis_broker = RedisBroker(url=settings.redis_url)
dramatiq.set_broker(redis_broker)


# ─── 任务 ───


@dramatiq.actor(max_retries=3, min_backoff=1000, max_backoff=30000)
def ingest_document(document_id: str) -> None:
    """异步摄取文档任务。

    1. 从数据库读取 Document 记录
    2. 从 MinIO 下载原始文件
    3. MIME 检测 → Parser Registry
    4. 解析 → 标准化 Block
    5. 结构化分块 → Chunk
    6. Embedding → Qdrant 写入
    7. 更新 Document 状态
    """
    # TODO: Phase 2 实现
    print(f"Ingesting document {document_id}")


@dramatiq.actor(max_retries=2)
def reindex_document(document_id: str) -> None:
    """重新索引文档（版本更新时触发）。"""
    print(f"Reindexing document {document_id}")


@dramatiq.actor(max_retries=1)
def delete_document_vectors(document_id: str, kb_id: str) -> None:
    """删除文档的向量索引。"""
    print(f"Deleting vectors for document {document_id}")


if __name__ == "__main__":
    # 启动 Worker
    worker = dramatiq.Worker(redis_broker, worker_timeout=100)
    worker.run()
