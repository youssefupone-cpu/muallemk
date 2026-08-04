"""تقسيم نص الكتاب إلى وحدات ودروس (P2-21).

استراتيجية حتمية (بلا LLM): تُكتشف العناوين بأنماط عربية/ماركداون، وتُجمَع
الأسطر المتتالية في درس واحد حتى العنوان التالي. إن لم تُعثر على أي عنوان
يُستخدم تقسيم حجمي متساوٍ كبديل (fallback) حتى لا يفشل التحليل أبداً.
"""

from __future__ import annotations

import re

# أنماط العناوين — سطر مستقل قصير يبدأ بواحد منها (يحتمل ترقيماً مختلطاً)
_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+|(?:الفصل|الوحدة|الدرس|الباب|الجزء|القسم|التدريب)\s*[\dIVX٠-٩0-9]*[\s:.-]*|[\dIVX٠-٩0-9]+\s*[.:-]\s+)"
)

# عناوين زائفة تُتجاهل (ترويسة/تذييل/أرقام صفحات)
_NOISE = re.compile(
    r"^\s*(?:صفحة\s*\d+|المملكة|جمهورية|وزارة|محافظة|التعليم|إدارة|مدرسة|الصفحة\s*\d+|Page\s*\d+|\d{1,3})\s*$",
    re.IGNORECASE,
)

_MIN_HEADING_LEN = 1
_MAX_HEADING_LEN = 120
_TARGET_CHARS = 6_000  # حجم درس مستهدف تقريباً (للتقسيم الحجمي)
_MIN_CHARS_PER_LESSON = 600


def _heading_title(line: str) -> str | None:
    s = line.strip()
    if not s or len(s) > _MAX_HEADING_LEN:
        return None
    if _NOISE.match(s):
        return None
    if _HEADING_RE.match(s):
        title = _HEADING_RE.sub("", s).strip(" :.-–")
        return title or s
    return None


def _is_unit(heading: str) -> bool:
    return bool(re.match(r"^(الفصل|الوحدة|الباب|الجزء|القسم)\b", heading, re.IGNORECASE))


def _chunks_by_volume(lines: list[str]) -> list[tuple[str, str]]:
    """fallback حجمي: يوزّع الأسطر على دروس متساوية الحجم."""
    text = "\n".join(lines)
    if not text.strip():
        return []
    n = max(1, round(len(text) / _TARGET_CHARS))
    per = max(_MIN_CHARS_PER_LESSON, len(text) // n)
    parts: list[str] = []
    buf = ""
    for ln in lines:
        if buf and len(buf) + len(ln) > per and len(buf) >= _MIN_CHARS_PER_LESSON:
            parts.append(buf)
            buf = ln
        else:
            buf += ("\n" if buf else "") + ln
    if buf.strip():
        parts.append(buf)
    return [(f"جزء {i + 1}", p.strip()) for i, p in enumerate(parts) if p.strip()]


def split_book(text: str) -> list[dict]:
    """يُقسّم النص إلى [{unit_index, unit_title, title, text}] — أبداً لا يفشل.

    - إذا وُجدت عناوين: كل عنوان يفتح درساً؛ عناوين الوحدات/الفصول تُعامل
      كرؤوس وحدات تُجمَّع تحتها الدروس المتتالية.
    - إن لم تظهر أي عناوين → تقسيم حجمي (fallback).
    """
    lines = text.splitlines()
    lessons: list[dict] = []
    cur_unit = 0
    cur_unit_title = ""
    cur: dict | None = None

    def flush() -> None:
        nonlocal cur
        if cur and cur["text"].strip():
            lessons.append(cur)
        cur = None

    for raw in lines:
        title = _heading_title(raw)
        if title is not None:
            flush()
            if _is_unit(title):
                cur_unit = len(lessons)  # وحدات تُرتّب بحسب ترتيب ظهور الدروس
                cur_unit_title = title
            cur = {
                "unit_index": cur_unit,
                "unit_title": cur_unit_title,
                "title": title,
                "text": "",
            }
        elif cur is not None:
            cur["text"] += ("\n" if cur["text"] else "") + raw
        # أسطر قبل أي عنوان: تُتجاهل (مقدمة/غلاف)
    flush()

    if not lessons:
        return [
            {"unit_index": 0, "unit_title": "", "title": t, "text": tx}
            for t, tx in _chunks_by_volume(lines)
        ]

    # وحدة افتراضية "الكتاب كاملاً" للدروس التي سبقت أول عنوان وحدة
    for lesson in lessons:
        lesson["unit_title"] = lesson["unit_title"] or "الكتاب"
    return lessons
