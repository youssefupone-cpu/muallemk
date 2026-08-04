"""مسارات مكتبة الكتب — رفع → تحليل → توليد → عرض/حذف (P2)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile

from app.books import service
from app.books.models import (
    BookDetail,
    BookOut,
    GenerateRequest,
    GenerateResult,
    GuardianReport,
    LessonContent,
    LessonOut,
    TemplateDetection,
)
from app.core.config import get_settings
from app.core.llm.factory import get_llm
from app.core.rate_limit import rate_limiter
from app.documents.service import (
    BLOCKED_MIME,
    SUPPORTED_EXTENSIONS,
    _extension,
    extract_text,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/books", tags=["books"])

MAX_BOOK_MB = 100  # الكتب أكبر من المستندات العادية — حد خاص (P2-19)


def _book_out(d: dict) -> BookOut:
    return BookOut(
        id=d["id"],
        filename=d["filename"],
        title=d.get("title") or "",
        file_type=d.get("file_type") or "pdf",
        status=d.get("status") or "uploaded",
        unit_count=d.get("unit_count") or 0,
        lesson_count=d.get("lesson_count") or 0,
        created_at=d["created_at"],
        updated_at=d.get("updated_at") or "",
    )


@router.post("/upload", response_model=BookOut)
async def upload_book(
    file: UploadFile,
    _: None = Depends(rate_limiter(get_settings().rate_limit_per_minute)),
):
    """يرفع كتاباً (PDF/DOCX/EPUB/نص...) ويستخرج نصه (P2-19)."""
    filename = file.filename or "book"
    ext = _extension(filename)
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"امتداد غير مدعوم للكتب: {ext} — المسموح: "
            + ", ".join(sorted(SUPPORTED_EXTENSIONS)),
        )
    # فحص MIME أساسي عبر المحتوى — لا نثق بالاسم
    head = file.file.read(512)
    file.file.seek(0)
    mime_guess = _mime_of(head)
    if mime_guess in BLOCKED_MIME:
        raise HTTPException(status_code=415, detail="نوع الملف محظور")
    # حد الحجم
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_BOOK_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"الكتاب يتجاوز {MAX_BOOK_MB}MB — ارفع ملفاً أصغر",
        )

    text = extract_text(file)
    if not text.strip():
        raise HTTPException(status_code=422, detail="تعذّر استخراج نص من الكتاب")
    book_id = service.create_book(filename, ext.lstrip("."), text)
    return _book_out(service.get_book(book_id))


def _mime_of(head: bytes) -> str:
    """تقدير MIME من البايتات الأولى — حماية خفيفة من HTML مقنّع."""
    lower = head[:512].lower()
    if b"<html" in lower or b"<!doctype html" in lower:
        return "text/html"
    if b"<svg" in lower:
        return "image/svg+xml"
    return "application/octet-stream"


@router.get("", response_model=list[BookOut])
async def books():
    return [_book_out(b) for b in service.list_books()]


@router.get("/search")
async def search_generated_lessons(q: str = "", book_id: int | None = None):
    """بحث نصي سريع في الدروس المولّدة (P2-77) — عنوان/شرح/أسئلة/مصطلحات."""
    return service.search_lessons(q, book_id=book_id)


@router.get("/templates/{book_id}", response_model=TemplateDetection)
async def detect_book_template(book_id: int):
    """التعرف على بنية كتاب الوزارة (P2-63) — Connect / Time for English."""
    if service.get_book(book_id) is None:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود")
    return service.detect_book_template(book_id)


@router.get("/{book_id}/guardian-report", response_model=GuardianReport)
async def book_guardian_report(book_id: int, days: int = 7):
    """تقرير ولي الأمر الأسبوعي (P2-64): تقدم + نشاط + نقاط ضعف."""
    if service.get_book(book_id) is None:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود")
    return service.guardian_report(book_id, days)


@router.get("/quiz/export")
async def export_quiz(book_id: int | None = None):
    """تصدير بنك الأسئلة JSON (P2-131) — كتاب كامل أو الكل."""
    if book_id is not None and service.get_book(book_id) is None:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود")
    return {
        "count": len(service.export_quiz_json(book_id)),
        "items": service.export_quiz_json(book_id),
    }


@router.post("/quiz/import")
async def import_quiz(req: dict):
    """استيراد بنك أسئلة JSON (P2-131) — body: {book_id, lesson_id?, items:[...]}."""
    book_id = int(req.get("book_id", 0))
    lesson_id = req.get("lesson_id")
    items = req.get("items") or []
    if service.get_book(book_id) is None:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود")
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=422, detail="items فارغ — لا شيء يُستورد")
    try:
        inserted = service.import_quiz_json(book_id, lesson_id, items)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"imported": inserted}


@router.get("/{book_id}", response_model=BookDetail)
async def book_detail(book_id: int):
    book = service.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود")
    lessons = service.list_lessons(book_id)
    units: dict[int, dict] = {}
    for lesson in lessons:
        u = units.setdefault(
            lesson["unit_index"],
            {
                "index": lesson["unit_index"],
                "title": lesson["unit_title"],
                "lessons": [],
            },
        )
        u["lessons"].append(LessonOut(**lesson))
    return BookDetail(book=_book_out(book), units=list(units.values()))


@router.post("/{book_id}/analyze", response_model=list[LessonOut])
async def analyze(
    book_id: int,
    _: None = Depends(rate_limiter(5)),  # استهلاك LLM — حد 5 طلبات/دقيقة
):
    """يحلّل بنية الكتاب إلى وحدات/دروس (P2-20/21). استهلاك LLM — محدود."""
    if service.get_book(book_id) is None:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود")
    lessons = service.analyze_book(book_id)
    if not lessons:
        raise HTTPException(
            status_code=422,
            detail="لم يُستخرج نص كافٍ لبناء الدروس — تأكد من جودة الملف",
        )
    return [LessonOut(**lesson) for lesson in lessons]


@router.post("/{book_id}/generate", response_model=GenerateResult)
async def generate(
    book_id: int,
    req: GenerateRequest,
    x_provider_key: str | None = Header(default=None, alias="x-provider-key"),
    _: None = Depends(rate_limiter(3)),  # استهلاك LLM كثيف — حد 3 طلبات/دقيقة
):
    """يولّد دروساً (شرح+أسئلة+تدريب) بالتسلسل — مهلة لكل درس بلا حجب الطلب (P2-22..25).

    مفتاح المزوّد يأتي من Header `x-provider-key` لتجنب التسريق في body.
    """
    if service.get_book(book_id) is None:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود")
    settings = get_settings()
    api_key = x_provider_key or req.api_key  # header تُفضّل
    llm = get_llm(
        provider=req.provider or settings.default_provider,
        model=req.model or settings.default_model,
        api_key=api_key,
        base_url=req.base_url or settings.ollama_base_url,
    )
    result = await service.generate_lessons(llm, book_id, req)
    return GenerateResult(**result)


@router.get("/lessons/{lesson_id}", response_model=LessonContent)
async def lesson_detail(lesson_id: int):
    lesson = service.get_lesson(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="الدرس غير موجود")
    return LessonContent(**lesson)


@router.post("/lessons/{lesson_id}/regenerate", response_model=GenerateResult)
async def regenerate_lesson(
    lesson_id: int,
    req: GenerateRequest,
    x_provider_key: str | None = Header(default=None, alias="x-provider-key"),
    _: None = Depends(rate_limiter(10)),  # حد 10 طلبات/دقيقة لتجديد الدروس
):
    """إعادة توليد درس واحد (P2-31) — بغض النظر عن حالته (ready/failed).

    يُعيد كتابة الشرح/الأسئلة/التدريب/المصطلحات ويحدّث بنك الأسئلة والملفات.
    مفتاح المزوّد يأتي من Header `x-provider-key`.
    """
    lesson = service.get_lesson(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="الدرس غير موجود")
    settings = get_settings()
    api_key = x_provider_key or req.api_key  # header تُفضّل
    llm = get_llm(
        provider=req.provider or settings.default_provider,
        model=req.model or settings.default_model,
        api_key=api_key,
        base_url=req.base_url or settings.ollama_base_url,
    )
    try:
        await service.generate_lesson(
            llm, lesson_id, req.grade_level, req.temperature, req.max_tokens
        )
    except Exception as e:
        logger.warning(
            "Lesson regeneration failed (lesson_id=%s) — sanitized error returned",
            lesson_id,
            exc_info=e,
        )
        raise HTTPException(
            status_code=502,
            detail="فشل توليد الدرس — تأكد من اتصال النموذج وحاول مرة أخرى.",
        ) from e
    return GenerateResult(generated=[lesson_id], failed=[])


@router.get("/{book_id}/quiz")
async def book_quiz(book_id: int, lesson_id: int | None = None):
    """أسئلة بنك الأسئلة لكتاب (P2-28) — اختيارياً لدرس واحد."""
    return service.list_quiz(book_id=book_id, lesson_id=lesson_id)


@router.post("/quiz/{quiz_id}/attempt")
async def quiz_attempt(quiz_id: int, req: dict):
    """يسجّل محاولة إجابة (P2-30) — مقارنة بسيطة بالإجابة النموذجية."""

    payload = req if isinstance(req, dict) else {}
    answer = str(payload.get("answer", ""))
    row = service.get_quiz(quiz_id)
    if row is None:
        raise HTTPException(status_code=404, detail="السؤال غير موجود")
    expected_row = service._quiz_expected(row)
    return service.record_attempt(quiz_id, answer, expected_row)


@router.get("/{book_id}/profile")
async def book_al_azhar_profile(book_id: int):
    """ركن الأزهر (P2-65): تمثيل مادة أزهرية للكتاب بناءً على العنوان."""
    book = service.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود")
    return service.al_azhar_profile(book["title"] or book["filename"])


@router.get("/{book_id}/progress")
async def book_progress(book_id: int):
    """تقدّم مذاكرة الكتاب (P2-30) — درس مكتمل + دقة الأسئلة."""
    if service.get_book(book_id) is None:
        raise HTTPException(status_code=404, detail="الكتاب غير موجود")
    return service.book_progress(book_id)


@router.post("/train/start")
async def train_start(req: dict):
    """يبدأ جلسة تدريب تفاعلية (P2-29) — يعيد السؤال الأول + token الجلسة."""
    lesson_id = int(req.get("lesson_id", 0))
    lesson = service.get_lesson(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="الدرس غير موجود")
    return service.start_training(lesson_id)


@router.post("/train/answer")
async def train_answer(req: dict):
    """يقدّم إجابة على السؤال الحالي (P2-29) — تصحيح فوري + السؤال التالي/ملخص."""
    token = str(req.get("token", ""))
    answer = str(req.get("answer", ""))
    if not token:
        raise HTTPException(status_code=400, detail="token الجلسة مطلوب")
    result = service.submit_training_answer(token, answer)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete("/{book_id}")
async def delete_book(book_id: int):
    if not service.delete_book(book_id):
        raise HTTPException(status_code=404, detail="الكتاب غير موجود")
    return {"deleted": book_id}
