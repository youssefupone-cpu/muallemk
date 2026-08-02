"""مزوّد احتياطي متوافق مع OpenAI — لأي مزوّد مخصّص (custom).

يُستخدم فقط عند تعيين provider=custom مع base_url صريح ومفتاح — معزول تماماً
عن LiteLLM (لو فشل أحدهما لا يتأثر الآخر). Anthropic عبر OpenAI-compat ليس
مدعوماً رسمياً، لذا هذا المسار للمزوّدات المخصّصة فقط.
"""

import logging
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.core.llm.base import BaseLLM

logger = logging.getLogger(__name__)


class OpenAICompatProvider(BaseLLM):
    """توافق OpenAI مباشر عبر openai SDK مع base_url مخصّص."""

    def __init__(self, model: str, base_url: str, api_key: str = "sk-not-needed"):
        self.provider = "custom"
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self._client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        kwargs: dict[str, Any] = {"temperature": temperature}
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if tools:
            kwargs["tools"] = tools
        resp = await self._client.chat.completions.create(
            model=self.model, messages=messages, **kwargs
        )
        return resp.choices[0].message.content or ""

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        kwargs: dict[str, Any] = {"temperature": temperature}
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if tools:
            kwargs["tools"] = tools
        stream = await self._client.chat.completions.create(
            model=self.model, messages=messages, stream=True, **kwargs
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def embed(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in resp.data]
