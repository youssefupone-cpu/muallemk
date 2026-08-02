"""مزوّد LiteLLM — 140+ مزوّداً عبر بادئات موحّدة.

المزوّدون المدعومون: ollama (محلي) / openai / anthropic / gemini / mistral /
groq / deepseek / openrouter — وكل بادئة تُمرَّر كما هي إلى LiteLLM.
المفاتيح تُقرأ من متغيرات البيئة (OPENAI_API_KEY، ANTHROPIC_API_KEY، ...).
"""

import logging
from collections.abc import AsyncIterator
from typing import Any

import litellm

from app.core.llm.base import BaseLLM

logger = logging.getLogger(__name__)

# المزوّدون المدمجون المعروفون لدى LiteLLM (إضافة أي مزوّد جديد = سطر واحد هنا)
KNOWN_PROVIDERS = {
    "ollama": "ollama",
    "openai": "openai",
    "anthropic": "anthropic",
    "gemini": "gemini",
    "mistral": "mistral",
    "groq": "groq",
    "deepseek": "deepseek",
    "openrouter": "openrouter",
}


class LiteLLMProvider(BaseLLM):
    """تطبيق LiteLLM — الواجهة الموحّدة لكل المزوّدين."""

    def __init__(self, model: str, provider: str = "ollama", base_url: str | None = None):
        if provider not in KNOWN_PROVIDERS:
            raise ValueError(f"مزوّد غير معروف لـ LiteLLM: {provider}")
        self.provider = provider
        self.model = model
        self.base_url = base_url

    def _litellm_model(self, provider: str | None = None) -> str:
        """تحويل (مزوّد + نموذج) إلى معرّف LiteLLM مثل `ollama/qwen2.5:7b`."""
        p = provider or self.provider
        return f"{KNOWN_PROVIDERS[p]}/{self.model}"

    def _completion_kwargs(self, temperature: float, max_tokens: int | None) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"temperature": temperature}
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if self.provider == "ollama" and self.base_url:
            kwargs["api_base"] = self.base_url
        return kwargs

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> str:
        model = self._litellm_model()
        kwargs = self._completion_kwargs(temperature, max_tokens)
        if tools:
            kwargs["tools"] = tools
        resp = await litellm.acompletion(model=model, messages=messages, **kwargs)
        return resp.choices[0].message.content or ""

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        model = self._litellm_model()
        kwargs = self._completion_kwargs(temperature, max_tokens)
        if tools:
            kwargs["tools"] = tools
        try:
            stream = await litellm.acompletion(
                model=model, messages=messages, stream=True, **kwargs
            )
        except Exception:
            logger.exception("فشل بدء تدفق الاستجابة عبر LiteLLM")
            raise
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

    async def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._litellm_model()
        kwargs = self._completion_kwargs(0.0, None)
        if self.provider == "ollama":
            # تضمين عبر نماذج ollama (مثل bge-m3) — يُستدعى صراحةً بمعرّف التضمين
            model = f"ollama/{self.model}"
        resp = await litellm.aembedding(model=model, input=texts, **kwargs)
        return [item["embedding"] for item in resp.data]
