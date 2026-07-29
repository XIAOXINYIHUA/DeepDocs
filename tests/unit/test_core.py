"""项目结构冒烟测试。"""

from __future__ import annotations


def test_imports() -> None:
    """验证所有核心模块可导入。"""
    from packages.core.config.settings import Settings, settings

    assert Settings
    assert settings is not None
    assert settings.postgres_server == "localhost"


def test_models_import() -> None:
    from packages.core.models import (
        Base,
        BlockModel,
        BlockType,
        Chunk,
        Citation,
        Document,
        DocumentStatus,
        DocumentVersion,
        IndexProfile,
        KnowledgeBase,
        User,
        Workspace,
    )

    assert Base
    assert DocumentStatus
    assert BlockType
    assert BlockModel


def test_providers_import() -> None:
    from packages.providers.base import ChatProvider, EmbeddingProvider, RerankProvider

    assert ChatProvider
    assert EmbeddingProvider
    assert RerankProvider


def test_deepseek_provider() -> None:
    from packages.providers.deepseek.adapter import DeepSeekChatProvider, _estimate_cost

    assert DeepSeekChatProvider
    cost = _estimate_cost("deepseek-chat", 100, 50)
    assert cost > 0


def test_exceptions() -> None:
    from packages.core.exceptions import (
        ProviderError,
        ParsingError,
        EmbeddingMismatch,
        UnsupportedFormat,
    )

    assert issubclass(ParsingError, Exception)
    assert issubclass(UnsupportedFormat, ParsingError)


def test_parser_registry() -> None:
    from packages.parsers.registry import ParserRegistry, detect_format

    registry = ParserRegistry()
    assert not registry.supported_formats()

    # 格式检测
    pdf_header = b"%PDF-1.4"
    assert detect_format("test.pdf", pdf_header) == "pdf"

    # 扩展名检测
    txt_content = b"hello world"
    assert detect_format("notes.md", txt_content) == "markdown"
    assert detect_format("data.csv", txt_content) == "csv"
    assert detect_format("doc.json", txt_content) == "json"


def test_retrieval_import() -> None:
    from packages.retrieval import (
        QdrantHybridRetriever,
        SearchResult,
        CitationVerifier,
    )

    assert QdrantHybridRetriever
    assert SearchResult
    assert CitationVerifier


def test_build_rag_prompt() -> None:
    from packages.retrieval.context import build_rag_prompt

    query = "什么是 RAG？"
    chunks = [
        {"text": "RAG 是检索增强生成。", "file_name": "doc.pdf", "page_number": 1},
    ]
    prompt, selected, tokens = build_rag_prompt(query, chunks, max_tokens=4096)
    assert "RAG" in prompt
    assert len(selected) == 1
    assert tokens > 0
