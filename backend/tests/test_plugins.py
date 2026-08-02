"""اختبارات م9 — منصة الإضافات: دورة حياة + عزل فشل + تخزين معزول.

تستخدم إضافات تجريبية حقيقية من مجلد plugins/ وواحدة مكسورة.
"""

import asyncio
import json
from pathlib import Path

from app.plugins.manager import (
    MAX_CONSECUTIVE_FAILURES,
    Plugin,
    PluginContext,
    discover_plugins,
)
from app.plugins.manifest import PluginManifest, PluginType

PLUGINS_DIR = Path(__file__).resolve().parent.parent / "plugins"


def load(name: str) -> Plugin:
    p = next((x for x in discover_plugins(PLUGINS_DIR) if x.info.name == name), None)
    assert p is not None, f"إضافة {name} غير موجودة"
    return p


def test_plugins_discovered():
    names = {p.info.name for p in discover_plugins(PLUGINS_DIR)}
    assert {"grades-tool", "study-table", "books", "broken-plugin"} <= names


def test_load_tool_plugin_and_invoke(tmp_path):
    p = load("grades-tool")
    assert p.load_module() is True
    assert p.enabled

    async def _go():
        return await p.run(grades=[{"subject": "م", "grade": 80}, {"subject": "ع", "grade": 100}])

    res = asyncio.run(_go())
    assert res["average"] == 90.0
    assert res["count"] == 2


def test_plugin_context_isolated_storage(tmp_path):
    ctx = PluginContext(tmp_path / "p")
    ctx.write_json("books.json", {"titles": ["أ"]})
    assert ctx.read_json("books.json") == {"titles": ["أ"]}
    assert (tmp_path / "p" / "books.json").exists()


def test_data_source_books_actions(tmp_path):
    # نسخة معزولة داخل tmp_path حتى لا تتداخل مع الكتابة الفعلية
    root = tmp_path / "books"
    (root / "data").mkdir(parents=True, exist_ok=True)
    src = PLUGINS_DIR / "books"
    for f in ("manifest.json", "run.py"):
        (root / f).write_text((src / f).read_text(encoding="utf-8"), encoding="utf-8")
    p = Plugin(
        root,
        PluginManifest.model_validate_json((root / "manifest.json").read_text(encoding="utf-8")),
    )
    assert p.load_module() is True
    res = asyncio.run(p.run(action="add", payload={"title": "الرياضيات", "author": "خالد"}))
    assert res["added"]["title"] == "الرياضيات"
    listed = asyncio.run(p.run(action="list"))
    assert len(listed["books"]) == 1


async def test_broken_plugin_fails_then_disabled_after_3_failures():
    p = load("broken-plugin")
    assert p.load_module() is True
    for _ in range(MAX_CONSECUTIVE_FAILURES):
        out = await p.run()
        assert out is None
    assert p.info.status.value == "disabled"
    assert p.info.failures >= MAX_CONSECUTIVE_FAILURES
    assert "تعطيل تلقائي" in p.info.last_error


def test_invalid_manifest_rejected(tmp_path):
    (tmp_path / "bad").mkdir()
    (tmp_path / "bad" / "manifest.json").write_text(
        json.dumps({"name": "X!", "version": "nope", "type": "tool"}), encoding="utf-8"
    )
    discovered = discover_plugins(tmp_path)
    assert all(p.info.name != "X!" for p in discovered)


def test_ui_page_manifest_declares_schema():
    p = load("study-table")
    assert p.manifest.type == PluginType.UI_PAGE
    assert "schema" in p.manifest.ui
    assert p.manifest.ui["schema"]["type"] == "array"


def test_data_source_for_rag_without_books_returns_empty(tmp_path):
    """م9.2: الربط بخط RAG — بلا كتب، يُرجع قائمة فارغة دون ضجيج."""
    root = tmp_path / "books"
    (root / "data").mkdir(parents=True, exist_ok=True)
    src = PLUGINS_DIR / "books"
    for f in ("manifest.json", "run.py"):
        (root / f).write_text((src / f).read_text(encoding="utf-8"), encoding="utf-8")
    p = Plugin(
        root,
        PluginManifest.model_validate_json((root / "manifest.json").read_text(encoding="utf-8")),
    )
    assert p.load_module() is True
    r = asyncio.run(p.run(action="for-rag"))
    assert r == {"books": []}


def test_ui_page_storage_roundtrip(tmp_path):
    """م9.1: التخزين المعزول لصفحات ui-page (data/ui.json عبر PluginContext)."""
    root = tmp_path / "study-table"
    (root / "data").mkdir(parents=True, exist_ok=True)
    src = PLUGINS_DIR / "study-table"
    (root / "manifest.json").write_text(
        (src / "manifest.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    p = Plugin(
        root,
        PluginManifest.model_validate_json((root / "manifest.json").read_text(encoding="utf-8")),
    )
    assert p.load_module() is True
    p.ctx.write_json(
        "ui.json", {"items": [{"day": "السبت", "subject": "رياضيات", "time": "09:00"}]}
    )
    data = p.ctx.read_json("ui.json")
    assert data["items"][0]["subject"] == "رياضيات"
    assert (root / "data" / "ui.json").exists()


# --- خطأ invoke مشروح (رسالة خطأ واضحة في الاستجابة) ---


def test_http_invoke_reports_error_then_success():
    """معزول عن ترتيب الاختبارات: نعيد تمكين grades-tool قبل كل سيناريو.

    - استدعاء بباراميتر خاطئ → status=error مع رسالة خطأ واضحة.
    - إعادة تمكين، ثم استدعاء صحيح → status=enabled مع النتيجة.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    c = TestClient(app)

    # 1) إعادة تمكين قوية + استدعاء خاطئ → خطأ مشروح
    c.post("/plugins/grades-tool/enable")
    r = c.post("/plugins/grades-tool/invoke", json={"subject": "رياضيات", "grade": 85})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "error"
    assert body["error"], "يجب أن تُعرَض رسالة خطأ (last_error) مع status=error"

    # 2) إعادة تمكين + استدعاء صحيح → نجاح
    c.post("/plugins/grades-tool/enable")
    r = c.post(
        "/plugins/grades-tool/invoke",
        json={"grades": [{"subject": "م", "grade": 80}, {"subject": "ع", "grade": 90}]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "enabled"
    assert body["result"]["average"] == 85.0
