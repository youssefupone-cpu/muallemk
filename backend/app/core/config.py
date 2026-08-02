"""إعدادات التطبيق — تُقرأ من متغيرات البيئة (.env) عبر pydantic-settings.

مفاتيح المزوّدين تُمرَّر من الواجهة (صفحة الإعدادات) لكل طلب، لذا لا توجد
مفاتيح إجبارية هنا. القيم الافتراضية تعمل مع المزوّد المحلي (Ollama).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "معلّمك"
    host: str = "0.0.0.0"
    port: int = 8000

    # المزوّد الافتراضي (محلي أولاً)
    default_provider: str = "ollama"
    default_model: str = "gemma3:1b-it-qat"
    ollama_base_url: str = "http://localhost:11434"

    # RAG — تضمين محلي عبر Ollama (nomic-embed-text افتراضياً؛ يُمكن تجاوزه عبر .env)
    rag_embed_model: str = "nomic-embed-text"
    rag_top_k: int = 8

    # البحث على الويب — Tavily (إن وُجد مفتاح) ثم SearXNG محلي
    tavily_api_key: str = ""
    searxng_url: str = "http://localhost:8080"

    # تخزين محلي
    data_dir: str = "data"


@lru_cache
def get_settings() -> Settings:
    return Settings()
