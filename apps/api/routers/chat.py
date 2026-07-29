"""文档研究引擎 —— 问答 / 总结 / 比较 / 抽取 API。"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.config.settings import settings
from packages.core.exceptions import ProviderError
from packages.core.models.document import Document, DocumentStatus
from packages.core.models.user import User
from packages.providers.base import ChatMessage
from packages.providers.deepseek.adapter import DeepSeekChatProvider
from packages.retrieval.citation import Citation, CitationVerifier
from packages.retrieval.context import build_rag_prompt
from packages.retrieval.hybrid import QdrantHybridRetriever

from ..dependencies.auth import get_current_user
from ..dependencies.database import get_db

router = APIRouter(tags=["research"])


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4096)
    mode: str = Field(
        default="qa",
        pattern=r"^(qa|summary|compare|extract|direct)$",
    )
    model: str | None = None
    top_k: int = Field(default=10, ge=1, le=50)
    rerank_top_k: int = Field(default=6, ge=1, le=20)
    similarity_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    stream: bool = True


class CitationResponse(BaseModel):
    file_name: str
    page_number: int | None = None
    heading_path: str | None = None
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationResponse] = []
    mode: str
    model: str


# ─── 核心路由 ───


@router.post("/knowledge-bases/{kb_id}/chat")
async def chat_with_kb(
    kb_id: str,
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """与知识库对话。

    5 种模式:
    - qa:     问答（需提供引用证据）
    - summary:文档总结
    - compare:多文档比较
    - extract:结构化抽取
    - direct: 直接对话（不检索）
    """
    provider = DeepSeekChatProvider(
        api_key=settings.deepseek_api_key,
        timeout=120,
    )

    # ─── direct 模式：不检索 ───
    if req.mode == "direct":
        messages = [
            ChatMessage(role="system", content="你是一个 AI 助手。"),
            ChatMessage(role="user", content=req.question),
        ]
        response = await provider.chat(
            messages=messages,
            model=req.model or "deepseek-chat",
        )
        return ChatResponse(
            answer=response.content,
            citations=[],
            mode="direct",
            model=response.model,
        )

    # ─── 检索模式 ───
    try:
        chunks = await _retrieve_chunks(
            kb_id=kb_id,
            query=req.question,
            top_k=req.top_k,
            rerank_top_k=req.rerank_top_k,
            threshold=req.similarity_threshold,
        )

        if not chunks:
            return ChatResponse(
                answer="根据知识库中的文档，找不到足够信息来回答。请换个问法或上传更多相关文档。",
                citations=[], mode=req.mode,
                model=req.model or "deepseek-chat",
            )

        # 构建 RAG prompt
        system_prompt = _get_mode_prompt(req.mode)

        prompt_text, selected_chunks, _ = build_rag_prompt(
            query=req.question,
            chunks=chunks,
            system_prompt=system_prompt,
            max_tokens=settings.max_context_tokens,
        )

        # ─── 流式 ───
        if req.stream:
            return StreamingResponse(
                _stream_answer(
                    provider=provider,
                    prompt=prompt_text,
                    chunks=chunks,
                    model=req.model,
                    temperature=req.temperature,
                ),
                media_type="text/event-stream",
            )

        # ─── 非流式 ───
        messages = [
            ChatMessage(role="user", content=prompt_text),
        ]
        response = await provider.chat(
            messages=messages,
            model=req.model or "deepseek-chat",
            temperature=req.temperature,
        )

        verifier = CitationVerifier()
        citation_result = verifier.verify(response.content, chunks)

        return ChatResponse(
            answer=response.content,
            citations=[
                CitationResponse(
                    file_name=c.file_name,
                    page_number=c.page_number,
                    heading_path=c.heading_path,
                    excerpt=c.excerpt[:200],
                )
                for c in citation_result.citations
            ],
            mode=req.mode,
            model=response.model,
        )

    except ProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service error: {e.message}",
        )


@router.post("/knowledge-bases/{kb_id}/summary")
async def summarize_kb(
    kb_id: str,
    doc_ids: list[str] | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """生成知识库 / 选定文档的摘要。"""
    query = select(Document).where(
        Document.kb_id == kb_id,
        Document.status == DocumentStatus.READY,
    )
    if doc_ids:
        query = query.where(Document.id.in_(doc_ids))
    result = await db.execute(query)
    docs = result.scalars().all()

    if not docs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No documents found",
        )

    file_list = "\n".join([f"- {d.filename} ({d.file_type})" for d in docs])
    question = f"请总结以下文档的内容:\n{file_list}"

    req = ChatRequest(question=question, mode="summary", stream=False)
    return await chat_with_kb(kb_id, req, current_user, db)


# ─── 检索 ───


async def _retrieve_chunks(
    kb_id: str,
    query: str,
    top_k: int = 10,
    rerank_top_k: int = 6,
    threshold: float = 0.6,
) -> list[dict[str, Any]]:
    """从 Qdrant 检索相关 chunk。"""
    from packages.providers.bge.embedding import BGEM3Embedding

    embedder = BGEM3Embedding(device="cpu")
    query_vector = await embedder.embed_query(query)

    retriever = QdrantHybridRetriever(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
    )

    collection_name = f"kb_{kb_id.replace('-', '_')}"
    results = retriever.search(
        collection_name=collection_name,
        dense_vector=query_vector,
        top_k=top_k,
    )

    # 过滤低分 + 取 top
    filtered = [r for r in results if r.score >= threshold]
    top = filtered[:rerank_top_k]

    return [
        {
            "chunk_id": r.chunk_id,
            "document_id": r.document_id,
            "file_name": r.metadata.get("file_name", "") if r.metadata else "",
            "text": r.text,
            "page_number": r.page_number,
            "heading_path": r.heading_path,
            "score": r.score,
        }
        for r in top
    ]


# ─── Prompt ───


def _get_mode_prompt(mode: str) -> str:
    prompts = {
        "qa": (
            "你是一个专业的文档分析助手。请基于提供的文档内容回答问题。\n"
            "你的回答必须严格基于提供的证据。\n"
            "对于每个关键事实，在括号内标注来源（文件名，页码）。\n"
            "如果证据不足以回答，请明确告知用户，不要编造。"
        ),
        "summary": (
            "你是一个文档分析助手。请基于以下文档内容生成摘要。\n"
            "按照章节、主题或时间线组织摘要。\n"
            "每个关键点标注来源（文件名，页码）。\n"
            "如果有多个文档，分别总结再综述。"
        ),
        "compare": (
            "你是一个文档比较专家。请对比以下文档的异同。\n"
            "按照关键维度横向对比。\n"
            "差异点高亮标注。\n"
            "每个发现标注来源（文件名，页码）。"
        ),
        "extract": (
            "你是一个信息抽取助手。请从文档中提取用户要求的字段信息。\n"
            "以结构化格式（JSON）输出。\n"
            "每个字段标注来源（文件名，页码）。\n"
            "如果字段不存在，标记为 null。"
        ),
    }
    return prompts.get(mode, prompts["qa"])


# ─── 流式输出 ───


async def _stream_answer(
    provider: DeepSeekChatProvider,
    prompt: str,
    chunks: list[dict[str, Any]],
    model: str | None = None,
    temperature: float = 0.3,
) -> AsyncIterator[str]:
    """SSE 流式输出。"""
    full_answer = ""
    try:
        messages = [ChatMessage(role="user", content=prompt)]
        async for text in provider.stream(
            messages=messages,
            model=model or "deepseek-chat",
            temperature=temperature,
        ):
            full_answer += text
            yield f"data: {json.dumps({'type': 'text', 'content': text}, ensure_ascii=False)}\n\n"

        # 引用校验
        verifier = CitationVerifier()
        citation_result = verifier.verify(full_answer, chunks)

        for c in citation_result.citations:
            citation_data = {
                "type": "citation",
                "citation": {
                    "file_name": c.file_name,
                    "page_number": c.page_number,
                    "heading_path": c.heading_path,
                    "excerpt": c.excerpt[:200],
                },
            }
            yield f"data: {json.dumps(citation_data, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
