"""Provider 抽象接口 —— LLM / Embedding / Reranker 适配器基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ChatMessage:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class ChatResponse:
    content: str
    model: str
    usage: dict | None = None  # {"prompt_tokens": ..., "completion_tokens": ...}
    cost_usd: float | None = None


class ChatProvider(ABC):
    """LLM 对话 Provider。"""

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """非流式对话。"""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """流式对话 —— 逐 chunk 产出文本。"""
        ...

    @abstractmethod
    async def structured_output(
        self,
        messages: list[ChatMessage],
        schema: dict[str, Any],
        model: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """结构化输出 —— 要求 LLM 返回符合 schema 的 JSON。"""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """检查 Provider 服务是否可用。"""
        ...

    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """估算文本 token 数（字节级近似或模型精确）。"""
        ...


class EmbeddingProvider(ABC):
    """嵌入向量 Provider。"""

    @abstractmethod
    async def embed_documents(
        self, texts: list[str]
    ) -> tuple[list[list[float]], list[list[float]] | None]:
        """文档嵌入 —— 返回 (dense, sparse_optional)。
        sparse 为 None 时表示不支持稀疏向量。
        """
        ...

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """查询嵌入 —— 单向量。"""
        ...

    @abstractmethod
    def dimension(self) -> int:
        """向量维度。"""
        ...

    @abstractmethod
    def signature(self) -> str:
        """模型签名 —— provider::model::dimension::version。"""
        ...


@dataclass
class RerankResult:
    index: int
    score: float
    text: str


class RerankProvider(ABC):
    """重排 Provider。"""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int = 10,
    ) -> list[RerankResult]:
        """对文档按 query 相关性重排。"""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
