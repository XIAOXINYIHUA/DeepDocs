"""上下文预算与构建 —— 选择证据块并组装 prompt。"""

from __future__ import annotations

from ..core.config.settings import settings


def estimate_tokens(text: str) -> int:
    """快速 token 估算（1 token ≈ 1.8 个中文字符）。"""
    import math
    return math.ceil(len(text) / 1.8)


def build_rag_prompt(
    query: str,
    chunks: list[dict],
    system_prompt: str | None = None,
    max_tokens: int | None = None,
) -> tuple[str, list[dict], int]:
    """构建 RAG prompt —— 在上下文预算内选择最优证据块。

    Returns:
        (final_prompt, selected_chunks, total_tokens)
    """
    max_tokens = max_tokens or settings.max_context_tokens

    # 默认 system prompt
    if system_prompt is None:
        system_prompt = (
            "你是一个专业的文档分析助手。请基于提供的文档内容回答问题。\n"
            "你的回答必须严格基于提供的证据。\n"
            "对于每个关键事实，在括号内标注来源（文件名，页码）。\n"
            "如果证据不足以回答，请明确告知用户，不要编造。"
        )

    # 构建证据上下文
    context_parts: list[str] = []
    selected_chunks: list[dict] = []
    total_factual_tokens = 0

    # 保留 tokens 给 system + query + 输出
    system_tokens = estimate_tokens(system_prompt)
    query_tokens = estimate_tokens(query)
    reserved_output = 2048  # 保留输出空间
    context_budget = max_tokens - system_tokens - query_tokens - reserved_output
    context_budget = max(context_budget, 1024)

    for chunk in chunks:
        text = chunk.get("text", "")
        source = chunk.get("file_name", "unknown")
        page = chunk.get("page_number")
        heading = chunk.get("heading_path")

        # 格式化引用头
        ref = f"[来源: {source}"
        if page:
            ref += f" 第{page}页"
        if heading:
            ref += f" | {heading}"
        ref += "]"

        entry = f"{ref}\n{text}"
        entry_tokens = estimate_tokens(entry)

        if total_factual_tokens + entry_tokens > context_budget:
            break

        context_parts.append(entry)
        selected_chunks.append(chunk)
        total_factual_tokens += entry_tokens

    # 拼接完整 prompt
    context = "\n\n---\n\n".join(context_parts)

    final_prompt = (
        f"{system_prompt}\n\n"
        "=== 文档证据 ===\n"
        f"{context}\n\n"
        "=== 用户问题 ===\n"
        f"{query}\n\n"
        "=== 回答 ===\n"
        "请基于以上证据给出回答。"
    )

    total = system_tokens + query_tokens + total_factual_tokens + reserved_output

    return final_prompt, selected_chunks, total
