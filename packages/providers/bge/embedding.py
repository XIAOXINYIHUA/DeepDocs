"""本地 BGE-M3 Embedding Provider。"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..base import EmbeddingProvider


class BGEM3Embedding(EmbeddingProvider):
    """BAAI/bge-m3 本地 Embedding 模型。

    支持：
    - Dense 向量（1024 维）
    - Sparse 向量（词汇权重）
    """

    def __init__(self, model_path: str | Path | None = None, device: str = "cpu"):
        self.model_path = Path(model_path) if model_path else None
        self.device = device
        self._model = None
        self._tokenizer = None

    def _load(self) -> None:
        """懒加载模型。"""
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            model_name = str(self.model_path) if self.model_path else "BAAI/bge-m3"
            self._model = SentenceTransformer(model_name, device=self.device)
        except ImportError:
            raise RuntimeError(
                "sentence-transformers 未安装。运行: pip install deepdocs[bge]"
            )

    async def embed_documents(
        self, texts: list[str]
    ) -> tuple[list[list[float]], list[list[float]] | None]:
        self._load()
        assert self._model is not None

        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        dense = embeddings.tolist() if isinstance(embeddings, np.ndarray) else embeddings
        return dense, None  # BGE-M3 sparse 支持待实现

    async def embed_query(self, text: str) -> list[float]:
        self._load()
        assert self._model is not None

        embedding = self._model.encode(
            text,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        if isinstance(embedding, np.ndarray):
            return embedding.tolist()
        return embedding

    def dimension(self) -> int:
        return 1024

    def signature(self) -> str:
        return "bge-m3::BAAI/bge-m3::1024::1.0"
