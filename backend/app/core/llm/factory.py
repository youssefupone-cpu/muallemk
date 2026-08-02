"""مصنع المزوّدين — يختار التنفيذ الصحيح حسب اسم المزوّد من الإعدادات."""

from app.core.llm.base import BaseLLM
from app.core.llm.litellm_provider import KNOWN_PROVIDERS, LiteLLMProvider
from app.core.llm.openai_compat import OpenAICompatProvider

ALL_PROVIDERS = [*KNOWN_PROVIDERS.keys(), "custom"]


def list_providers() -> list[str]:
    """كل المزوّدين المدعومين."""
    return list(ALL_PROVIDERS)


def get_llm(
    provider: str,
    model: str,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
) -> BaseLLM:
    """يُرجع مزوّد النماذج المناسب.

    - مزوّدات LiteLLM المعروفة → LiteLLMProvider.
    - `custom` → OpenAICompatProvider (يتطلب base_url).
    - غير المعروف → ValueError.
    """
    if provider in KNOWN_PROVIDERS:
        return LiteLLMProvider(model=model, provider=provider, base_url=base_url)
    if provider == "custom":
        if not base_url:
            raise ValueError("المزوّد المخصّص يتطلب base_url")
        return OpenAICompatProvider(
            model=model, base_url=base_url, api_key=api_key or "sk-not-needed"
        )
    raise ValueError(f"مزوّد غير معروف: {provider} (المتاح: {ALL_PROVIDERS})")
