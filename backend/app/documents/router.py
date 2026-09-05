"""مسارات المستندات — الاستيراد والتحويل والإدارة."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.db import get_connection
from app.core.rate_limit import rate_limiter
from app.documents.models import DocumentContent, DocumentOut
from app.documents.service import (
    IMAGE_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    _extension,
    extract_text,
)
from app.rag.router import get_engine

router = APIRouter(prefix="/documents", tags=["documents"])

PREVIEW_LEN = 120
MAX_DOC_MB = 50  # حد حجم المستند (DoS) — P2-19 / bug 2026-08-02


def _row_to_doc(row) -> DocumentOut:
    return DocumentOut(
        id=row["id"],
        filename=row["filename"],
        file_type=row["file_type"],
        preview=row["content"][:PREVIEW_LEN] if row["content"] else "",
        created_at=row["created_at"],
    )


def _check_size(file: UploadFile, max_mb: int = MAX_DOC_MB) -> None:
    """يفحص حجم الملف قبل قراءته بالكامل — يرفع 413 عند التجاوز."""
    try:
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
    except Exception:
        return  # بعض الـ streams لا تدعم seek — نكمل
    if size and size > max_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"الملف يتجاوز {max_mb}MB — ارفع ملفاً أصغر",
        )


@router.post("", response_model=DocumentOut, status_code=200)
async def upload_document(
    file: UploadFile = File(...),
    _: None = Depends(rate_limiter(30)),
):
    """يرفع ملفاً ويستخرج نصه (markitdown أو OCR للصور) ثم يخزّنه."""
    ext = _extension(file.filename or "")
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"نوع الملف غير مدعوم: {ext or 'غير معروف'}")

    _check_size(file)

    try:
        content = extract_text(file)
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e)) from e
    if not content.strip():
        raise HTTPException(status_code=422, detail="تعذّر استخراج نص من الملف")

    file_type = "image" if ext in IMAGE_EXTENSIONS else "document"
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO documents (filename, file_type, content) VALUES (?, ?, ?)",
            (file.filename or "unnamed", file_type, content),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id, filename, file_type, content, created_at FROM documents WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
    return _row_to_doc(row)


@router.get("", response_model=list[DocumentOut])
async def list_documents():
    """قائمة المستندات (بدون المحتوى الكامل)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, filename, file_type, content, created_at FROM documents ORDER BY id DESC"
        ).fetchall()
    return [_row_to_doc(r) for r in rows]


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(doc_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, filename, file_type, content, created_at FROM documents WHERE id = ?",
            (doc_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="المستند غير موجود")
    return _row_to_doc(row)


@router.get("/{doc_id}/content", response_model=DocumentContent)
async def get_document_content(doc_id: int):
    """المحتوى الكامل للمستند — يُستخدم لاحقاً في RAG ومعاينة الدراسة."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, filename, content FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="المستند غير موجود")
    return DocumentContent(id=row["id"], filename=row["filename"], content=row["content"])


@router.delete("/{doc_id}")
async def delete_document(doc_id: int):
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="المستند غير موجود")
    # حذف من فهرس المتجهات أيضاً حتى لا تبقى نتائج بحث لمستندات محذوفة
    await get_engine().remove_document(doc_id)
    return {"deleted": doc_id}
