"""混合检索 —— Dense + Sparse + RRF Fusion。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from qdrant_client import QdrantClient, models

from ..core.config.settings import settings


@dataclass
class SearchResult:
    chunk_id: str
    document_id: str
    kb_id: str
    text: str
    score: float
    page_number: int | None = None
    heading_path: str | None = None
    block_type: str | None = None
    metadata: dict[str, Any] | None = None


class QdrantHybridRetriever:
    """基于 Qdrant 的混合检索器。

    使用两个 named vectors：
    - "dense": 稠密向量（cosine 距离）
    - "sparse": 稀疏向量（BM25 等价）
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        api_key: str | None = None,
    ):
        self.client = QdrantClient(
            host=host or settings.qdrant_host,
            port=port or settings.qdrant_port,
            api_key=api_key or settings.qdrant_api_key or None,
        )

    def ensure_collection(
        self,
        collection_name: str,
        dense_dim: int = 1024,
        on_disk: bool = True,
    ) -> None:
        """确保集合存在，支持 dense + sparse 双向量。"""
        collections = self.client.get_collections().collections
        if any(c.name == collection_name for c in collections):
            return

        self.client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dense": models.VectorParams(
                    size=dense_dim,
                    distance=models.Distance.COSINE,
                    on_disk=on_disk,
                ),
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(
                    index=models.SparseIndexParams(
                        on_disk=on_disk,
                    )
                ),
            },
            optimizers_config=models.OptimizersConfigDiff(
                indexing_threshold=20000,
            ),
        )

    def insert(
        self,
        collection_name: str,
        point_id: str,
        dense_vector: list[float],
        sparse_vector: dict[str, list[float]] | None,
        payload: dict[str, Any],
    ) -> None:
        """写入单个向量。"""
        vectors: dict[str, Any] = {"dense": dense_vector}
        if sparse_vector:
            vectors["sparse"] = models.SparseVector(
                indices=list(sparse_vector.keys()),
                values=list(sparse_vector.values()),
            )

        self.client.upsert(
            collection_name=collection_name,
            points=[models.PointStruct(id=point_id, vector=vectors, payload=payload)],
        )

    def insert_batch(
        self,
        collection_name: str,
        points: list[models.PointStruct],
    ) -> None:
        """批量写入。"""
        self.client.upsert(collection_name=collection_name, points=points)

    def search(
        self,
        collection_name: str,
        dense_vector: list[float],
        sparse_vector: dict[str, float] | None = None,
        top_k: int = 50,
        filters: dict[str, Any] | None = None,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5,
    ) -> list[SearchResult]:
        """混合检索。

        1. Dense ANN 搜索
        2. Sparse 搜索（如果提供）
        3. RRF Fusion 合并结果
        """
        query_filter = None
        if filters:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key=k,
                        match=models.MatchValue(value=v),
                    )
                    for k, v in filters.items()
                ]
            )

        # Dense 搜索
        dense_result = self.client.query_points(
            collection_name=collection_name,
            query=dense_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        # 合并结果（无 sparse 时直接用 dense）
        if not sparse_vector:
            return [
                SearchResult(
                    chunk_id=point.id,
                    document_id=point.payload.get("document_id", ""),
                    kb_id=point.payload.get("kb_id", ""),
                    text=point.payload.get("text", ""),
                    score=point.score,
                    page_number=point.payload.get("page_number"),
                    heading_path=point.payload.get("heading_path"),
                    block_type=point.payload.get("block_type"),
                    metadata=point.payload,
                )
                for point in dense_result.points
            ]

        raise NotImplementedError("Sparse + RRF fusion 待实现")

    def delete_by_document(
        self, collection_name: str, document_id: str
    ) -> None:
        """删除文档的所有向量。"""
        self.client.delete(
            collection_name=collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )

    def delete_collection(self, collection_name: str) -> None:
        self.client.delete_collection(collection_name)
