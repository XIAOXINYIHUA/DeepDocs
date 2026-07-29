"""DeepSeek Chat/Reasoner Provider 适配器。"""

from __future__ import annotations

from typing import Any, AsyncIterator

import httpx
import structlog

from ..base import ChatMessage, ChatProvider, ChatResponse

logger = structlog.get_logger()


class DeepSeekChatProvider(ChatProvider):
    """DeepSeek 官方 API 适配器。

    支持：
    - deepseek-chat（默认对话）
    - deepseek-reasoner（复杂推理，思考链可见）
    """

    BASE_URL = "https://api.deepseek.com"

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.timeout = timeout

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _format_messages(
        self, messages: list[ChatMessage]
    ) -> list[dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in messages]

    def estimate_tokens(self, text: str) -> int:
        """估算 token 数（DeepSeek 约 1 token / 1.8 个中文字符）。"""
        import math
        return math.ceil(len(text) / 1.8)

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.base_url}/v1/models",
                    headers=self._build_headers(),
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        model = model or "deepseek-chat"
        payload = {
            "model": model,
            "messages": self._format_messages(messages),
            "temperature": temperature,
            **kwargs,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self._build_headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

            choice = data["choices"][0]
            usage = data.get("usage", {})
            cost = _estimate_cost(
                model=model,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
            )

            return ChatResponse(
                content=choice["message"]["content"],
                model=data["model"],
                usage={
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "total_tokens": usage.get("total_tokens"),
                    "reasoning_tokens": (
                        usage.get("completion_tokens_details", {})
                        .get("reasoning_tokens")
                    ),
                },
                cost_usd=cost,
            )

    async def stream(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        model = model or "deepseek-chat"
        payload = {
            "model": model,
            "messages": self._format_messages(messages),
            "temperature": temperature,
            "stream": True,
            **kwargs,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                headers=self._build_headers(),
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    chunk = line[6:]
                    if chunk == "[DONE]":
                        break
                    import json
                    try:
                        data = json.loads(chunk)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

    async def structured_output(
        self,
        messages: list[ChatMessage],
        schema: dict[str, Any],
        model: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """通过 response_format 约束输出为 JSON。"""
        model = model or "deepseek-chat"
        payload = {
            "model": model,
            "messages": self._format_messages(messages),
            "response_format": {"type": "json_object"},
            **kwargs,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self._build_headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]

        import json
        return json.loads(content)


def _estimate_cost(
    model: str, prompt_tokens: int, completion_tokens: int
) -> float:
    """粗略估算 DeepSeek 费用（美元）。"""
    # 参考价格：deepseek-chat $0.27/M input, $1.10/M output
    # deepseek-reasoner $0.55/M input, $2.19/M output
    if "reasoner" in model:
        return (prompt_tokens * 0.55 + completion_tokens * 2.19) / 1_000_000
    return (prompt_tokens * 0.27 + completion_tokens * 1.10) / 1_000_000
