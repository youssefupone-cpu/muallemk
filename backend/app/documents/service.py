"""خدمة المستندات — استخراج النص من أي ملف مدعوم عبر markitdown + OCR.

الملفات المدعومة: txt/md/html/csv/json/xml → نص مباشر؛ pdf/docx/pptx/xlsx/epub
عبر markitdown (إن توفرت محوّلاتها)؛ الصور عبر tesseract (ara+eng).
"""

import io
import logging
from pathlib import Path

from fastapi import UploadFile

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    # نصية مباشرة
    ".txt",
    ".md",
    ".html",
    ".htm",
    ".csv",
    ".json",
    ".xml",
    # وثائق
    ".pdf",
    ".docx",
    ".doc",
    ".pptx",
    ".ppt",
    ".xlsx",
    ".xls",
    ".epub",
    # صور (OCR)
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tiff",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}

# MIME types blocked for security (P4-240)
BLOCKED_MIME = {
    "text/html",
    "application/xhtml+xml",
    "application/x-executable",
    "application/x-msdownload",
    "application/x-bat",
    "application/x-sh",
}


def _extension(filename: str) -> str:
    return Path(filename).suffix.lower()


# حد قراءة الملفات في الذاكرة (DoS) — 50MB
MAX_READ_BYTES = 50 * 1024 * 1024
# حد أبعاد الصورة لمنع decompression bombs
MAX_IMAGE_PIXELS = 40_000_000  # ~40MP


def _extract_images(files: list[UploadFile]) -> str:
    """OCR للصور عبر tesseract (ara + eng)."""
    try:
        import pytesseract
        from PIL import Image

        # حماية من decompression bomb
        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    except ImportError:
        logger.warning("pytesseract/Pillow غير متوفرين — تخطّي OCR الصور")
        return ""

    parts: list[str] = []
    for f in files:
        try:
            img = Image.open(f.file)
            img.load()  # يفعّل فحص MAX_IMAGE_PIXELS
            w, h = img.size
            if w * h > MAX_IMAGE_PIXELS:
                logger.warning("صورة ضخمة تُرفض: %s (%sx%s)", f.filename, w, h)
                parts.append("")
                continue
            text = pytesseract.image_to_string(img, lang="ara+eng")
            parts.append(text.strip())
        except Exception:
            logger.exception("فشل OCR لصورة: %s", f.filename)
            parts.append("")
        finally:
            f.file.seek(0)
    return "\n".join(p for p in parts if p)


def extract_text(upload: UploadFile) -> str:
    """يحوّل ملفاً واحداً إلى نص ماركداون/خام.

    يقرأ حتى MAX_READ_BYTES + 1؛ إن تجاوز → يرفض (DoS).
    """
    ext = _extension(upload.filename or "")
    raw = upload.file.read(MAX_READ_BYTES + 1)
    if len(raw) > MAX_READ_BYTES:
        raise ValueError(f"الملف يتجاوز {MAX_READ_BYTES // (1024 * 1024)}MB")

    if not raw:
        return ""

    if ext in IMAGE_EXTENSIONS:
        upload.file.seek(0)
        return _extract_images([upload])

    # markitdown للنصوص والوثائق
    try:
        from markitdown import MarkItDown

        md = MarkItDown()
        result = md.convert_stream(
            io.BytesIO(raw),
            file_extension=ext or ".txt",
        )
        return (result.text_content or "").strip()
    except ImportError:
        logger.warning("markitdown غير متوفر — نصوص فقط")
        try:
            return raw.decode("utf-8", errors="replace").strip()
        except Exception:
            return ""
    except Exception:
        logger.exception("فشل التحويل عبر markitdown لملف: %s", upload.filename)
        return ""


def extract_text_many(files: list[UploadFile]) -> str:
    """يستخرج نصاً من عدة ملفات (للمستند): النصوص والوثائق ثم صور OCR."""
    text_files = [f for f in files if _extension(f.filename or "") not in IMAGE_EXTENSIONS]
    images = [f for f in files if _extension(f.filename or "") in IMAGE_EXTENSIONS]

    parts: list[str] = []
    for f in text_files:
        parts.append(extract_text(f))
    if images:
        parts.append(_extract_images(images))
    return "\n\n".join(parts)
