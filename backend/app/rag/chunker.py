"""تقطيع عربي مراعي للجمل والعناوين والفقرات.

استراتيجية: فقرات → جمل (نقاط/فواصل/أسئلة) → تجميع حتى سقف الحروف
مع منع قطع الجملة الواحدة (إلا إن تجاوزت سقفاً أكبر كوحدة واحدة).
"""

from __future__ import annotations

import re

# فواصل نهاية الجملة العربية/العامة (مع استثناء الأرقام العشرية والاختصارات)
_SENTENCE_SPLIT = re.compile(r"(?<=[\u0600-\u06FFA-Za-z0-9])(?:(?:[.!؟?؛;]+)|(?:\n{2,}))\s*")

_HEADING = re.compile(r"^(#{1,6})\s+(.+)$")

DEFAULT_CHUNK_CHARS = 800
MAX_SINGLE_SENTENCE = 1600
OVERLAP_CHARS = 60


def _has_arabic(text: str) -> bool:
    return any("\u0600" <= c <= "\u06ff" for c in text)


def split_sentences(text: str) -> list[str]:
    """يقطّع النص إلى جمل كاملة (يحافظ على علامات الترقيم بحدود)."""
    if not text:
        return []
    # وحدد رؤوس markdown كوحدات منفصلة
    parts: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            if current:
                parts.append("\n".join(current).strip())
                current = []
            continue
        if _HEADING.match(line.strip()):
            if current:
                parts.append("\n".join(current).strip())
                current = []
            parts.append(line.strip())
        else:
            current.append(line)
    if current:
        parts.append("\n".join(current).strip())

    # ثم قطّع الفقرات الطويلة إلى جمل
    sentences: list[str] = []
    for part in parts:
        if _HEADING.match(part):
            sentences.append(part)
            continue
        for seg in _SENTENCE_SPLIT.split(part):
            seg = seg.strip()
            if seg:
                sentences.append(seg)
    return [s for s in sentences if s]


def chunk_text(text: str, chunk_chars: int = DEFAULT_CHUNK_CHARS) -> list[str]:
    """يبني أجزاءً عربية من نص بحد سقف الحروف مع تداخل بسيط."""
    sentences = split_sentences(text)
    chunks: list[str] = []
    buff: list[str] = []
    buff_len = 0

    for s in sentences:
        s_len = len(s)
        # جملة أطول من MAX: تقطّع قسراً (حتى لو ضاعت تماسك الجملة)
        if s_len > max(chunk_chars, MAX_SINGLE_SENTENCE):
            if buff:
                chunks.append(" ".join(buff))
                buff, buff_len = [], 0
            for i in range(0, len(s), chunk_chars):
                chunks.append(s[i : i + chunk_chars])
            continue

        if buff and buff_len + s_len + 1 > chunk_chars:
            chunks.append(" ".join(buff))
            # تداخل: أعد آخر جملة قصيرة
            tail = buff[-1]
            buff = [tail[-OVERLAP_CHARS:]] if len(tail) > OVERLAP_CHARS else []
            buff_len = sum(len(x) for x in buff)
        buff.append(s)
        buff_len += s_len + 1

    if buff:
        chunks.append(" ".join(buff))
    return chunks


def chunk_with_heading(text: str, chunk_chars: int = DEFAULT_CHUNK_CHARS) -> list[dict]:
    """مثل chunk_text لكن مع مراعاة العناوين: تُدمج أولاً في الـ chunk.

    كل عنصر: {"heading": str | None, "text": str}
    """
    sentences = split_sentences(text)
    chunks: list[dict] = []
    buff_text: list[str] = []
    buff_len = 0
    last_heading: str | None = None

    for s in sentences:
        m = _HEADING.match(s)
        if m:
            # عنوان جديد — احفظ ما سبق وابدأ قسماً جديداً
            if buff_text:
                chunks.append({"heading": last_heading, "text": " ".join(buff_text)})
            last_heading = re.sub(r"^#+\s*", "", s)
            buff_text, buff_len = [], 0
            continue

        if buff_len + len(s) + 1 > chunk_chars and buff_text:
            chunks.append({"heading": last_heading, "text": " ".join(buff_text)})
            tail = buff_text[-1]
            buff_text = [tail[-OVERLAP_CHARS:]] if len(tail) > OVERLAP_CHARS else []
            buff_len = sum(len(x) for x in buff_text)
        buff_text.append(s)
        buff_len += len(s) + 1

    if buff_text:
        chunks.append({"heading": last_heading, "text": " ".join(buff_text)})
    return chunks


def chunk_index_text(text: str, chunk_chars: int = DEFAULT_CHUNK_CHARS) -> list[str]:
    """نسخة كاملة للتضمين: العنوان (إن وجد) + النص المعياري."""
    meta_chunks = chunk_with_heading(text, chunk_chars)
    out: list[str] = []
    for c in meta_chunks:
        parts = []
        if c["heading"]:
            parts.append(f"# {c['heading']}")
        if c["text"]:
            parts.append(c["text"])
        out.append("\n".join(parts))
    return out
