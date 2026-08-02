"""اختبارات طبقة النماذج (م2) — الواجهة الموحّدة والمزوّدون."""

import pytest

from app.core.llm.base import BaseLLM
from app.core.llm.factory import get_llm, list_providers
from app.core.llm.litellm_provider import LiteLLMProvider
from app.core.llm.openai_compat import OpenAICompatProvider


def test_base_llm_is_abstract():
    """BaseLLM واجهة تجريدية — لا يمكن إنشاؤها مباشرة."""
    with pytest.raises(TypeError):
        BaseLLM()  # type: ignore[abstract]


def test_litellm_model_prefixes():
    """كل مزوّد يُسبَق بالبادئة الصحيحة لـ LiteLLM."""
    p = LiteLLMProvider(model="qwen2.5:7b", base_url="http://localhost:11434")
    assert p._litellm_model("ollama") == "ollama/qwen2.5:7b"
    assert p._litellm_model("openai") == "openai/qwen2.5:7b"
    assert p._litellm_model("openrouter") == "openrouter/qwen2.5:7b"
    assert p._litellm_model("anthropic") == "anthropic/qwen2.5:7b"
    assert p._litellm_model("gemini") == "gemini/qwen2.5:7b"
    assert p._litellm_model("mistral") == "mistral/qwen2.5:7b"
    assert p._litellm_model("groq") == "groq/qwen2.5:7b"
    assert p._litellm_model("deepseek") == "deepseek/qwen2.5:7b"


def test_litellm_provider_defaults():
    p = LiteLLMProvider(model="qwen2.5:7b")
    assert p.provider == "ollama"
    assert p.base_url is None  # ollama المحلي لا يحتاج base_url إلا عند التخصيص


def test_openai_compat_provider_config():
    p = OpenAICompatProvider(
        model="custom-model", base_url="https://api.example.com/v1", api_key="k"
    )
    assert p.base_url == "https://api.example.com/v1"
    assert p.api_key == "k"


def test_factory_returns_litellm_for_known_providers():
    for provider in [
        "ollama",
        "openai",
        "anthropic",
        "gemini",
        "mistral",
        "groq",
        "deepseek",
        "openrouter",
    ]:
        llm = get_llm(provider, model="m")
        assert isinstance(llm, LiteLLMProvider), provider


def test_factory_custom_uses_openai_compat():
    llm = get_llm("custom", model="m", base_url="http://x/v1", api_key="k")
    assert isinstance(llm, OpenAICompatProvider)


def test_factory_unknown_provider_raises():
    with pytest.raises(ValueError):
        get_llm("nonexistent", model="m")


def test_list_providers_includes_all():
    providers = list_providers()
    assert "ollama" in providers
    assert "openai" in providers
    assert "openrouter" in providers
    assert "custom" in providers
