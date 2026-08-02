"""اختبارات م9.3 — إضافة "تقارير AI": تخزين معزول + نقطة REST (بدون شبكة)."""

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.plugins.manager import Plugin, PluginContext, discover_plugins
from app.plugins.manifest import PluginManifest, PluginType

PLUGINS_DIR = Path(__file__).resolve().parent.parent / "plugins"
REPORTS_SRC = PLUGINS_DIR / "reports"


def isolated_reports_plugin(tmp_path: Path) -> Plugin:
    """نسخة معزولة من إضافة reports داخل tmp_path (لا تتداخل مع التشغيل الفعلي)."""
    root = tmp_path / "reports"
    (root / "data").mkdir(parents=True, exist_ok=True)
    for f in ("manifest.json", "run.py"):
        (root / f).write_text((REPORTS_SRC / f).read_text(encoding="utf-8"), encoding="utf-8")
    p = Plugin(
        root,
        PluginManifest.model_validate_json((root / "manifest.json").read_text(encoding="utf-8")),
    )
    assert p.load_module() is True
    return p


def test_report_plugin_discovered_with_type():
    p = next((x for x in discover_plugins(PLUGINS_DIR) if x.info.name == "reports"), None)
    assert p is not None
    assert p.manifest.type == PluginType.REPORT
    assert p.manifest.permissions == ["storage.own"]


def test_report_plugin_save_list_open_delete(tmp_path):
    p = isolated_reports_plugin(tmp_path)

    saved = asyncio.run(
        p.run(
            action="save",
            payload={
                "topic": "التفاضل",
                "markdown": "# تقرير\n\nمحتوى [1]",
                "sources": [{"filename": "رياضيات.md", "score": 0.9}],
            },
        )
    )
    assert saved["saved"] == 1

    listed = asyncio.run(p.run(action="list"))
    assert len(listed["reports"]) == 1
    assert listed["reports"][0]["topic"] == "التفاضل"

    opened = asyncio.run(p.run(action="open", payload={"id": 1}))
    assert opened["markdown"].startswith("# تقرير")
    assert opened["sources"][0]["filename"] == "رياضيات.md"

    deleted = asyncio.run(p.run(action="delete", payload={"id": 1}))
    assert deleted["reports"] == 0


def test_report_plugin_storage_is_isolated(tmp_path):
    p = isolated_reports_plugin(tmp_path)
    asyncio.run(p.run(action="save", payload={"topic": "أ", "markdown": "م", "sources": []}))
    # التخزين معزول داخل بيانات الإضافة، لا في دليل العمل العام
    assert (tmp_path / "reports" / "data" / "reports.json").exists()
    assert not Path("data/reports.json").exists()


def test_http_report_endpoint_validates_empty_topic():
    """نقطة REST تُرفض الموضوع الفارغ (422) قبل أي استدعاء شبكة."""
    c = TestClient(app)
    r = c.post("/plugins/reports/report", json={"topic": "   "})
    assert r.status_code == 422
    assert "الموضوع فارغ" in r.json()["detail"]


def test_http_report_endpoint_rejects_non_report_plugin():
    """الإضافات من غير نوع report تُرفض (422) — التوليد للنوع المخصص فقط."""
    c = TestClient(app)
    r = c.post("/plugins/grades-tool/report", json={"topic": "رياضيات"})
    assert r.status_code == 422
    assert "report" in r.json()["detail"]


def test_report_plugin_ctx_data_dir_isolated(tmp_path):
    ctx = PluginContext(tmp_path / "reports" / "data")
    assert ctx.data_dir == tmp_path / "reports" / "data"
    assert ctx.data_dir.parent.name == "reports"
