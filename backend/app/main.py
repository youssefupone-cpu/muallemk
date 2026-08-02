"""معلّمك — مساعد الدراسة المصري/العربي.

نقطة دخول التطبيق (FastAPI). تسجيل التطبيقات الفرعية يحدث في مراحل لاحقة
(chat, documents, rag, websearch, plugins).
"""

from fastapi import FastAPI

from app.chat.router import router as chat_router
from app.core.config import get_settings
from app.core.db import init_db
from app.documents.router import router as documents_router
from app.plugins.router import router as plugins_router
from app.rag.router import router as rag_router
from app.websearch.router import router as websearch_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="مساعد دراسة ذكي — محلي أولاً، مع دعم كل مزوّدي LLM.",
    docs_url="/docs",
    redoc_url=None,
)


@app.on_event("startup")
async def startup():
    init_db()


app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(rag_router)
app.include_router(websearch_router)
app.include_router(plugins_router)


@app.get("/", include_in_schema=False)
async def root():
    return {"app": settings.app_name, "docs": "/docs"}


@app.get("/health", tags=["system"])
async def health():
    """فحص صحة الخدمة."""
    return {"status": "ok", "app": settings.app_name, "version": "0.1.0"}
