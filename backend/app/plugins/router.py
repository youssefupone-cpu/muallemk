"""مسارات إدارة الإضافات (م9) — قائمة/حالة/تفعيل/تعطيل/سجلات.

عزل الفشل هنا على مستوى دورة الحياة: تنفيذ الإضافة محاصر بمهلة
وحالة ثابتة تُحدَّث لكل إضافة، والتعطيل التلقائي بعد 3 إخفاقات في المدير.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from httpx import HTTPStatusError, RequestError

from app.core.config import get_settings
from app.core.db import get_connection
from app.core.llm.factory import get_llm
from app.plugins.manager import Plugin, discover_plugins
from app.plugins.report import ReportRequest, generate_report
from app.rag.embeddings import OllamaEmbedder
from app.rag.engine import RAGEngine
from app.rag.reranker import OllamaReranker

router = APIRouter(prefix="/plugins", tags=["plugins"])

# مجلد افتراضي: <backend>/plugins (يُستبدل من الإعدادات في real wiring)
plugins_cache: list[Plugin] = []


def get_plugins() -> list[Plugin]:
    global plugins_cache
    if not plugins_cache:
        plugins_cache = discover_plugins("plugins")
    return plugins_cache


@router.get("")
async def list_plugins():
    return [p.info.model_dump() for p in get_plugins()]


@router.post("/{name}/enable")
async def enable_plugin(name: str):
    p = _find(name)
    if p.load_module():
        return {"name": name, "status": p.info.status}
    return {"name": name, "status": p.info.status, "error": p.info.last_error}


@router.post("/{name}/disable")
async def disable_plugin(name: str):
    p = _find(name)
    p.disable()
    return {"name": name, "status": p.info.status}


@router.get("/{name}/logs")
async def plugin_logs(name: str):
    p = _find(name)
    data = p.ctx.read_json("logs.json") if (p.root / "data" / "logs.json").exists() else {}
    return {"name": name, "logs": data}


@router.get("/{name}/storage")
async def plugin_storage_get(name: str):
    """يقرأ مساحة التخزين المعزولة للإضافات عديمة entrypoint (ui-page).
    يُخزَّن في data/ui.json — نفس الـ PluginContext المعزول."""
    p = _find(name)
    if (p.root / "data" / "ui.json").exists():
        return p.ctx.read_json("ui.json")
    return {"items": []}


@router.put("/{name}/storage")
async def plugin_storage_put(name: str, body: dict):
    """يكتب مساحة التخزين المعزولة (data/ui.json)."""
    p = _find(name)
    p.ctx.write_json("ui.json", body)
    return {"name": name, "saved": True}


@router.post("/{name}/index-for-rag")
async def index_plugin_for_rag(name: str):
    """م9.2 — يمرر محتوى إضافة (مكتبة كتب) عبر خط RAG: إدراج + فهرسة."""
    p = _find(name)
    if p.info.type != "data-source":
        raise HTTPException(status_code=422, detail="فهرسة RAG للإضافات من نوع data-source فقط")
    if not p.enabled:
        p.load_module()
    res = await p.run(action="for-rag", payload=None)
    books = (res or {}).get("books") or []
    if not books:
        return {"name": name, "indexed": 0, "message": "لا كتب بعد — أضف كتباً أولاً"}

    settings = get_settings()
    engine = RAGEngine(
        uri=settings.data_dir + "/lancedb",
        embedder=OllamaEmbedder(base_url=settings.ollama_base_url, model=settings.rag_embed_model),
    )

    indexed = []
    try:
        for b in books:
            title = b.get("title", "بدون عنوان")
            author = b.get("author", "")
            content = f"# {title}\nالمؤلف: {author}\n" if author else f"# {title}\n"
            with get_connection() as conn:
                cur = conn.execute(
                    "INSERT INTO documents (filename, file_type, content) VALUES (?, ?, ?)",
                    (f"كتاب: {title}", "book", content),
                )
                doc_id = cur.lastrowid
                conn.commit()
            r = await engine.index_document(doc_id, f"كتاب: {title}", content)
            indexed.append({"document_id": doc_id, "title": title, "chunks": r["indexed"]})
    except (HTTPStatusError, RequestError, OSError) as e:
        base = settings.ollama_base_url
        raise HTTPException(
            status_code=503,
            detail=f"تعذّر استدعاء محرك التضمين (Ollama على {base}؟). تفاصيل: {e}",
        ) from e
    return {"name": name, "indexed": indexed}


@router.post("/{name}/invoke")
async def invoke_plugin(name: str, body: dict | None = None):
    """ينفّذ إجراءً داخل الإضافة (عزل زمني عبر Plugin.run).

    عند الفشل (ERROR/DISABLED) نُرفق `last_error` حتى يرى المستخدم السبب
    في الاستجابة مباشرة بدلاً من `result: null, status: error` بلا شرح."""
    p = _find(name)
    if not p.enabled:
        p.load_module()
    result = await p.run(**(body or {}))
    resp: dict = {"name": name, "result": result, "status": p.info.status}
    if p.info.status in ("error", "disabled"):
        resp["error"] = p.info.last_error
    return resp


@router.post("/{name}/report")
async def generate_report_endpoint(name: str, req: ReportRequest):
    """م9.3 — يولّد تقريراً أكاديمياً عند الطلب من إضافة نوع report.

    يسترجع مادة الموضوع من RAG ثم يطلب النموذج كتابة تقرير Markdown
    باستشهادات [ن] حقيقية، ويحفظ النتيجة في مساحة الإضافة المعزولة.
    """
    p = _find(name)
    if p.info.type != "report":
        raise HTTPException(status_code=422, detail="توليد تقارير للإضافات من نوع report فقط")
    topic = (req.topic or "").strip()
    if not topic:
        raise HTTPException(status_code=422, detail="الموضوع فارغ — اكتب موضوع التقرير")
    if not p.enabled:
        p.load_module()

    settings = get_settings()
    llm = get_llm(
        provider=req.provider or settings.default_provider,
        model=req.model or settings.default_model,
        api_key=req.api_key,
        base_url=req.base_url or settings.ollama_base_url,
    )
    engine = RAGEngine(
        uri=settings.data_dir + "/lancedb",
        embedder=OllamaEmbedder(base_url=settings.ollama_base_url, model=settings.rag_embed_model),
    )
    reranker = OllamaReranker(base_url=settings.ollama_base_url)

    try:
        result = await generate_report(
            llm=llm,
            engine=engine,
            topic=topic,
            top_k=req.top_k or settings.rag_top_k,
            reranker=reranker,
        )
    except (RequestError, OSError) as e:
        base = settings.ollama_base_url
        raise HTTPException(
            status_code=503,
            detail=f"تعذّر استدعاء محرك التضمين/النموذج (Ollama على {base}؟). تفاصيل: {e}",
        ) from e

    saved = await p.run(action="save", payload=result.model_dump())
    resp = result.model_dump()
    resp["report_ident"] = (saved or {}).get("saved")
    resp["plugin"] = name
    return resp


def _find(name: str):
    p = next((p for p in get_plugins() if p.info.name == name), None)
    if p is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="إضافة غير موجودة")
    return p
