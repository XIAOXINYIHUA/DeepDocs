"""本地 BGE Reranker Provider。"""

from __future__ import annotations

from pathlib import Path

from ..base import RerankProvider, RerankResult


class BGEReranker(RerankProvider):
    """BAAI/bge-reranker-v2-m3 本地重排模型。"""

    def __init__(self, model_path: str | Path | None = None, device: str = "cpu"):
        self.model_path = Path(model_path) if model_path else None
        self.device = device
        self._model = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import CrossEncoder
            model_name = (
                str(self.model_path)
                if self.model_path
                else "BAAI/bge-reranker-v2-m3"
            )
            self._model = CrossEncoder(model_name, device=self.device)
        except ImportError:
            raise RuntimeError(
                "sentence-transformers 未安装。运行: pip install deepdocs[bge]"
            )

    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int = 10,
    ) -> list[RerankResult]:
        self._load()
        assert self._model is not None

        pairs = [[query, doc] for doc in documents]
        scores = self._model.predict(pairs)

        # 按分数降序排列
        indexed = list(enumerate(scores))
        indexed.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in indexed[:top_k]:
            results.append(
                RerankResult(index=idx, score=float(score), text=documents[idx])
            )
        return results

    async def health_check(self) -> bool:
        try:
            self._load()
            return self._model is not None
        except Exception:
            return False
