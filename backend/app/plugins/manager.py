"""مدير الإضافات (م9) — اكتشاف، تحميل، دورة حياة، عزل فشل.

نقاط القوة المطلوبة من الخطة:
- دورة حياة: detected → validated → loaded → enabled → running → disabled/error.
- عزل فشل: مهلة تنفيذ + تعطيل إجبارياً بعد 3 إخفاقات متتالية.
- تخزين معزول: مجلد `data/<plugin>/` يُسلَّم عبر PluginContext فقط.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import sys
from pathlib import Path
from types import ModuleType

from app.plugins.manifest import (
    PluginInfo,
    PluginManifest,
    PluginStatus,
)

logger = logging.getLogger(__name__)

MAX_CONSECUTIVE_FAILURES = 3
CALL_TIMEOUT_SECONDS = 10


class PluginContext:
    """سياق آمن للإضافة: وصول مقصود للقراءة + تخزين معزول فقط."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def read_json(self, name: str) -> dict:
        return json.loads((self.data_dir / name).read_text(encoding="utf-8"))

    def write_json(self, name: str, data: dict) -> None:
        (self.data_dir / name).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )


class Plugin:
    def __init__(self, root: Path, manifest: PluginManifest):
        self.root = root
        self.manifest = manifest
        self._info = PluginInfo(
            name=manifest.name,
            version=manifest.version,
            type=manifest.type,
            title=manifest.title or manifest.name,
            description=manifest.description,
            permissions=manifest.permissions,
            ui=manifest.ui,
        )
        self._module: ModuleType | None = None
        self._ctx: PluginContext | None = None

    @property
    def info(self) -> PluginInfo:
        return self._info

    @property
    def ctx(self) -> PluginContext:
        if self._ctx is None:
            self._ctx = PluginContext(self.root / "data")
        return self._ctx

    def load_module(self) -> bool:
        """يحاول تحميل entrypoint (وحدة Python نسبية). يعيد True عند النجاح."""
        entry = self.manifest.entrypoint
        if not entry:
            self._info.status = PluginStatus.LOADED
            return True
        path = (self.root / entry).resolve()
        if not path.exists() or self.root.resolve() not in path.parents:
            self._info.last_error = "entrypoint غير صالح أو خارج مجلد الإضافة"
            self._info.status = PluginStatus.ERROR
            return False
        spec = importlib.util.spec_from_file_location(f"plugin_{self.manifest.name}", path)
        if spec is None or spec.loader is None:
            self._info.last_error = "تعذّر قراءة وحدة الإضافة"
            self._info.status = PluginStatus.ERROR
            return False
        try:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod
            spec.loader.exec_module(mod)
            self._module = mod
            self._info.status = PluginStatus.ENABLED
            return True
        except Exception as e:  # عزل فشل التحميل
            self._record_failure(f"تحميل فشل: {e}")
            return False

    @property
    def enabled(self) -> bool:
        return self._info.status in (PluginStatus.ENABLED, PluginStatus.RUNNING)

    async def run(self, *args, **kwargs):
        """ينفّذ entrypoint الإضافة محاطاً بمهلة (عزل فشل زمني).

        يتوقع تنفيذاً يعرّض دالة `run(ctx, *args, **kwargs)`. عند تجاوز
        المهلة أو رمي خطأ يُسجَّل كفشل ويُعاد None.
        """
        if self._info.status == PluginStatus.DISABLED:
            return None
        mod = self._module
        if mod is None or not hasattr(mod, "run"):
            self._record_failure("الإضافة لا تحدد run(ctx)")
            return None
        self._info.status = PluginStatus.RUNNING
        try:
            return await asyncio.wait_for(
                mod.run(self.ctx, *args, **kwargs),
                timeout=CALL_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            self._record_failure(f"مهلة التنفيذ تجاوزت {CALL_TIMEOUT_SECONDS} ثوانٍ")
        except Exception as e:
            self._record_failure(f"فشل التنفيذ: {e}")
        finally:
            if self.enabled:
                self._info.status = PluginStatus.ENABLED
        return None

    def disable(self, reason: str = "تعطيل يدوي") -> None:
        self._info.status = PluginStatus.DISABLED
        self._info.last_error = reason

    def _record_failure(self, error: str) -> None:
        self._info.failures += 1
        self._info.last_error = error
        self._info.status = PluginStatus.ERROR
        if self._info.failures >= MAX_CONSECUTIVE_FAILURES:
            self._disable(f"تعطيل تلقائي بعد {self._info.failures} إخفاقات")
            logger.warning("إضافة %s عُطِّلت تلقائياً (%s)", self._info.name, error)

    def _disable(self, reason: str) -> None:
        self._info.status = PluginStatus.DISABLED
        self._info.last_error = reason


def discover_plugins(plugins_dir: str | Path) -> list[Plugin]:
    root = Path(plugins_dir)
    plugins: list[Plugin] = []
    if not root.exists():
        return plugins
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith("_"):
            continue
        manifest_path = child / "manifest.json"
        if not manifest_path.exists():
            continue
        try:
            manifest = PluginManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("إضافة %s: manifest غير صالح — %s", child.name, e)
            continue
        plugins.append(Plugin(child, manifest))
    return plugins
