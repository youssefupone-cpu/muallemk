"""تبعية RAG الموحّدة — محرك Singleton عبر app.state (P2-136).

يحلّ محل الإنشاء المتكرر لـ RAGEngine في كل طلب (documents/plugins/router + rag).

- المحرك يُبنى مرة واحدة عند أول طلب، ويُعاد بناؤه تلقائياً عند تغيّر
  إعدادات RAG (data_dir / ollama_base_url / rag_embed_model).
- lifespan يحقن عادةً نسخة في app.state عبر `attach_rag_engine(app)`؛
  والوظيفة `get_engine()` تعمل أيضاً خارج FastAPI (اختبارات/سكربتات).
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from app.core.config import get_settings
from app.rag.embeddings import OllamaEmbedder
from app.rag.engine import RAGEngine

# نسخة العملية الوحيدة (يستعملها routes عبر dep، والاختبارات مباشرة)
_engine: RAGEngine | None = None
_engine_signature: tuple[str, str, str] | None = None


def build_rag_engine() -> RAGEngine:
    """يبني RAGEngine بإعدادات التطبيق الحالية."""
    settings = get_settings()
    return RAGEngine(
        uri=settings.data_dir + "/lancedb",
        embedder=OllamaEmbedder(base_url=settings.ollama_base_url, model=settings.rag_embed_model),
    )


def get_engine() -> RAGEngine:
    """يُعيد المحرك العالمي — يُعاد بناؤه تلقائياً عند تغيّر إعدادات RAG.

    متوافق مع `app.state.rag_engine` إذا حُقن عبر lifespan، وبخلافه
    (اختبارات/سكربتات مستقلة) يبني ويخزن نسخة عملية.
    """
    global _engine, _engine_signature
    settings = get_settings()
    signature = (settings.data_dir, settings.ollama_base_url, settings.rag_embed_model)
    if _engine is None or _engine_signature != signature:
        _engine = build_rag_engine()
        _engine_signature = signature
    return _engine


def require_rag_engine(app: FastAPI) -> None:
    """يُهيّئ app.state.rag_engine عند بدء التشغيل (يُستدعى من lifespan)."""
    app.state.rag_engine = get_engine()


def as_engine_dep(request: Any) -> RAGEngine:
    """dep FastAPI: يستقرأ app.state ثم يقع على النسخة العملية إن غابت."""
    state = getattr(request.app.state, "rag_engine", None)
    return state or get_engine()
