"""إضافة "تقارير AI" (م9.3) — تخزين معزول لنتائج التوليد داخل data/reports.json.

التوليد الفعلي يجري في النواة (app/plugins/report.py عبر RAG + LLM) لأن
الإضافات معزولة عن النموذج والفهرس؛ هنا تُدار دورة حياة التقارير فقط:
قائمة / فتح / حذف.
"""

import json
from datetime import date
from pathlib import Path

REPORTS_FILE = "reports.json"


def _load(ctx) -> list:
    path: Path = ctx.data_dir / REPORTS_FILE
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


async def run(ctx, action="list", payload=None):
    """يدير التقارير المحفوظة: list, save, open, delete."""
    reports = _load(ctx)
    if action == "list":
        return {
            "reports": [
                {"id": r["id"], "topic": r["topic"], "created_at": r["created_at"]} for r in reports
            ]
        }
    if action == "save":
        entry = {
            "id": 1 + (reports[-1]["id"] if reports else 0),
            "topic": (payload or {}).get("topic", ""),
            "markdown": (payload or {}).get("markdown", ""),
            "sources": (payload or {}).get("sources", []),
            "created_at": date.today().isoformat(),
        }
        reports.append(entry)
        _write(ctx, reports)
        return {"saved": entry["id"], "reports": len(reports)}
    if action == "open":
        rid = int((payload or {}).get("id", 0))
        for r in reports:
            if r["id"] == rid:
                return r
        return {"error": "تقرير غير موجود"}
    if action == "delete":
        rid = int((payload or {}).get("id", 0))
        reports = [r for r in reports if r["id"] != rid]
        _write(ctx, reports)
        return {"deleted": rid, "reports": len(reports)}
    return {"error": "إجراء غير معروف"}


def _write(ctx, reports: list) -> None:
    (ctx.data_dir / REPORTS_FILE).write_text(
        json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8"
    )
