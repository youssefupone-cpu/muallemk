"""عقود الإضافات (م9) — manifest صارم عبر Pydantic.

كل إضافة هي مجلد داخل `plugins/` يحوي `manifest.json` إجبارياً.
الأنواع:
  - tool: أداة تُدار يدوياً (تعرض/تنفذ إجراءً).
  - ui-page: صفحة RTL كاملة عبر UI تصريحي (بلا React — JSON Schema).
  - data-source: مصدر بيانات (مثل "الكتب") يُربط بخط RAG.
  - report: مولّد تقارير عند الطلب (ملخص + استشهادات → MD).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PluginType(StrEnum):
    TOOL = "tool"
    UI_PAGE = "ui-page"
    DATA_SOURCE = "data-source"
    REPORT = "report"


class PluginManifest(BaseModel):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,49}$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    min_core_version: str = Field(default="0.1.0", pattern=r"^\d+\.\d+\.\d+$")
    type: PluginType
    entrypoint: str | None = Field(
        default=None,
        description="وحدة Python (نقطة/ملف) تُنفَّذ للإضافة من نوع tool/report/data-source",
    )
    permissions: list[str] = Field(default_factory=list)
    title: str = Field(default="")
    description: str = Field(default="")
    # UI تصريحي لـ ui-page: {widget: "form"|"table"|...} أو مسودة JSON Schema
    ui: dict[str, Any] = Field(default_factory=dict)

    @field_validator("permissions")
    @classmethod
    def _restrict_permissions(cls, v: list[str]) -> list[str]:
        allowed = {"documents.read", "rag.query", "websearch", "storage.own"}
        for p in v:
            if p not in allowed:
                raise ValueError(f"صلاحية غير مسموحة في النواة: {p}")
        return v

    @field_validator("entrypoint")
    @classmethod
    def _no_abs_entrypoint(cls, v: str | None) -> str | None:
        if v and (v.startswith("/") or ".." in v):
            raise ValueError("entrypoint يجب أن يكون نسبياً داخل مجلد الإضافة")
        return v


class PluginStatus(StrEnum):
    DETECTED = "detected"
    VALIDATED = "validated"
    LOADED = "loaded"
    ENABLED = "enabled"
    RUNNING = "running"
    DISABLED = "disabled"
    ERROR = "error"


class PluginInfo(BaseModel):
    name: str
    version: str
    type: PluginType
    title: str
    description: str
    status: PluginStatus = PluginStatus.DETECTED
    failures: int = 0
    last_error: str = ""
    permissions: list[str] = Field(default_factory=list)
    ui: dict[str, Any] = Field(default_factory=dict)
