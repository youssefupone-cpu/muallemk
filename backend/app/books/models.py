"""نماذج (Schemas) مكتبة الكتب — التبادل بين الواجهة والخادم."""

from pydantic import BaseModel, Field


class BookUploadRequest(BaseModel):
    """بيانات كتاب تم رفعه (يُرفع نصه المفهرس بدل الملف الثنائي عبر الرابط)."""


class BookOut(BaseModel):
    id: int
    filename: str
    title: str = ""
    file_type: str = "pdf"
    status: str = "uploaded"
    unit_count: int = 0
    lesson_count: int = 0
    created_at: str
    updated_at: str = ""


class LessonOut(BaseModel):
    id: int
    book_id: int
    unit_index: int = 0
    unit_title: str = ""
    title: str
    status: str = "pending"
    created_at: str
    updated_at: str = ""


class BookDetail(BaseModel):
    book: BookOut
    units: list[dict] = Field(default_factory=list)  # [{index, title, lessons:[LessonOut]}]


class LessonContent(BaseModel):
    id: int
    book_id: int
    unit_index: int = 0
    unit_title: str = ""
    title: str
    status: str
    content: str = ""  # شرح
    questions: list[dict] = Field(default_factory=list)  # أسئلة
    exercises: list[dict] = Field(default_factory=list)  # تدريب
    glossary: list[dict] = Field(default_factory=list)  # مصطلحات (35)
    created_at: str = ""
    updated_at: str = ""


class GenerateRequest(BaseModel):
    lesson_ids: list[int] | None = None  # None = كل الدروس
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=32_768)
    grade_level: str = "متوسط"  # مبتدئ/متوسط/متقدم — مستوى اللغة في التوليد (P2-68)


class GenerateResult(BaseModel):
    generated: list[int]
    failed: list[dict] = Field(default_factory=list)  # [{lesson_id, error}]


class TemplateDetection(BaseModel):
    template_key: str
    name: str
    confidence: float


class GuardianReport(BaseModel):
    period_days: int
    progress: dict
    weekly_activity: dict
    accuracy_by_qtype: dict
    weak_points: list[str] = Field(default_factory=list)
