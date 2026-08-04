"""خدمة مكتبة الكتب — تحليل البنية وتوليد الدروس (شرح + أسئلة + تدريب).

دورة العمل (P2):
  upload → analyze (split_book → book_lessons) → generate (LLM لكل درس)
  → content جاهز في lesson؛ وبعد نجاح كل درس يُفهرس `شرح` تلقائياً في RAG (P2-27).

التوليد يتحمل الانقطاعات: درس فاشل لا يوقف البقية، ويُسجَّل خطؤه في الصف.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from app.books.models import GenerateRequest
from app.books.splitter import split_book
from app.core.config import get_settings
from app.core.db import get_connection
from app.core.llm.base import BaseLLM

logger = logging.getLogger(__name__)

# ----------------------- تخزين (SQLite) -----------------------

STATUSES = ("uploaded", "analyzed", "generating", "ready")
LESSON_STATUSES = ("pending", "generating", "ready", "failed")


def _book_row(row) -> dict:
    d = dict(row)
    d.pop("content", None)  # لا نرسل نص الكتاب كاملاً في القوائم
    return d


def create_book(filename: str, file_type: str, content: str, title: str = "") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO books (filename, title, file_type, content, status) "
            "VALUES (?, ?, ?, ?, 'uploaded')",
            (filename, title or filename, file_type, content),
        )
        conn.commit()
        return cur.lastrowid


_LESSON_COUNT_SQL = "(SELECT COUNT(*) FROM book_lessons l WHERE l.book_id = b.id) AS lesson_count"
_UNIT_COUNT_SQL = (
    "(SELECT COUNT(DISTINCT unit_index) FROM book_lessons l WHERE l.book_id = b.id) AS unit_count"
)


def list_books() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT b.*, "
            + _LESSON_COUNT_SQL
            + ", "
            + _UNIT_COUNT_SQL
            + " FROM books b ORDER BY b.created_at DESC"
        ).fetchall()
        return [_book_row(r) for r in rows]


def get_book(book_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT b.*, "
            + _LESSON_COUNT_SQL
            + ", "
            + _UNIT_COUNT_SQL
            + " FROM books b WHERE b.id = ?",
            (book_id,),
        ).fetchone()
        return dict(row) if row else None


def get_book_content(book_id: int) -> str:
    with get_connection() as conn:
        row = conn.execute("SELECT content FROM books WHERE id = ?", (book_id,)).fetchone()
        return row["content"] if row else ""


def set_book_status(book_id: int, status: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE books SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, book_id),
        )
        conn.commit()


def delete_book(book_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
        return cur.rowcount > 0


# ----------------------- الدروس -----------------------


def _lesson_row(row) -> dict:
    d = dict(row)
    for key in ("content", "questions", "exercises"):
        if key in d:
            d.pop(key)
    return d


def list_lessons(book_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, book_id, unit_index, unit_title, title, status, "
            "created_at, updated_at FROM book_lessons "
            "WHERE book_id = ? ORDER BY id",
            (book_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_lesson(lesson_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM book_lessons WHERE id = ?", (lesson_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        for key in ("questions", "exercises", "glossary"):
            if isinstance(d.get(key), str):
                d[key] = json.loads(d[key] or "[]")
        return d


def analyze_book(book_id: int) -> list[dict]:
    """يُقسّم محتوى الكتاب إلى دروس (P2-21) — يمسح أي دروس سابقة ويعيد البناء."""
    content = get_book_content(book_id)
    lessons = split_book(content)
    with get_connection() as conn:
        conn.execute("DELETE FROM book_lessons WHERE book_id = ?", (book_id,))
        for lesson in lessons:
            conn.execute(
                "INSERT INTO book_lessons "
                "(book_id, unit_index, unit_title, title, status) "
                "VALUES (?, ?, ?, ?, 'pending')",
                (book_id, lesson["unit_index"], lesson["unit_title"], lesson["title"]),
            )
        conn.execute(
            "UPDATE books SET status = 'analyzed', updated_at = datetime('now') WHERE id = ?",
            (book_id,),
        )
        conn.commit()
    return list_lessons(book_id)


# ----------------------- التوليد (LLM) -----------------------

GENERATE_SYSTEM = """أنت معلّمك، مولّد دروس عربي. تُعطى مقطعاً من كتاب طالب.
اكتب درساً تعليمياً كاملاً عنه بتنسيق JSON صارم — بلا أي نص خارج JSON:

{{
  "title": "عنوان الدرس",
  "شرح": "شرح وافٍ منسق بـ Markdown، بلغة عربية سليمة بمستوى "
         "{grade} وبلهجة مصرية ودودة خفيفة",
  "أسئلة": [
    {{"type": "mcq", "question": "...", "options": ["أ", "ب", "ج", "د"],
      "answer": 0, "explanation": "لماذا"}},
    {{"type": "true_false", "question": "...", "answer": true,
      "explanation": "..."}},
    {{"type": "complete", "question": "...", "answer": "..."}},
    {{"type": "essay", "question": "...", "answer": "إجابة نموذجية مختصرة"}}
  ],
  "تدريب": [
    {{"question": "سؤال تدريبي", "hint": "تلميح خطوة أولى",
      "answer": "إجابة خطوة بخطوة"}}
  ],
  "مصطلحات": [
    {{"term": "المصطلح", "definition": "تعريف مبسط بمستوى الطالب"}}
  ]
}}

القواعد:
- 5-8 أسئلة متنوعة الأنواع و3-5 تمارين تدريبية.
- كل معلومة في الشرح مستندة للمقطع المقدّم فقط — لا تختلق حقائق خارجية.
- إن كان المقطع قصيراً جداً أو غير ذي معنى فقل ذلك في الشرح بصراحة مع ألا تختلق.
- الأسئلة مرتبطة فعلياً بنص المقطع (لا أسئلة عامة).
"""


def _repair_json(text: str) -> str:
    """إصلاحات خفيفة لنتائج النماذج الصغيرة (فاصلة زائدة قبل إغلاق، تعليقات)."""
    # فاصلة زائدة قبل ] أو } داخل JSON (أشهر خطأ من gemma/qwen الصغيرة)
    s = re.sub(r",(\s*[\]}])", r"\1", text)
    # أسطر تعليق/شرح بعد JSON تُقصّ (أحدث ظهور }
    end = s.rfind("}")
    if end != -1:
        s = s[: end + 1]
    return s


def _extract_json(text: str) -> dict:
    """يستخرج JSON من رد النموذج — يتسامح مع أقسام ```json ... ``` أو نص زائد.

    محاولات: (1) النص كما هو بعد إصلاح خفيف، (2) داخل سياج markdown،
    (3) أول { ... آخر } خام — يفشل أخيراً بخطأ واضح.
    """
    if not text or not text.strip():
        raise ValueError("رد النموذج فارغ")

    candidates: list[str] = []
    s = text.strip()
    # 1) نص بلا سياج ثم آخر يقتطع بعد آخر } (أكثر سلاسة للنماذج الصغيرة)
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, re.DOTALL)
    if fence:
        candidates.append(fence.group(1))
    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(s[start : end + 1])
    candidates.append(s)

    for raw in candidates:
        repaired = _repair_json(raw)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            try:
                return json.loads(_repair_json(raw.rsplit("}", 1)[0] + "}"))
            except json.JSONDecodeError:
                continue
    raise ValueError("استجابة النموذج ليست JSON صالحاً — أعد المحاولة")


async def generate_lesson(
    llm: BaseLLM,
    lesson_id: int,
    grade_level: str,
    temperature: float | None,
    max_tokens: int | None,
) -> dict:
    """يولّد درساً واحداً (شرح+أسئلة+تدريب) ويخزّنه — يرفع استثناء عند الفشل."""
    lesson = get_lesson(lesson_id)
    if lesson is None:
        raise ValueError("درس غير موجود")
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE book_lessons SET status = 'generating', updated_at = datetime('now') "
                "WHERE id = ?",
                (lesson_id,),
            )
            conn.commit()
        return await _generate_lesson_impl(llm, lesson_id, grade_level, temperature, max_tokens)
    except Exception as e:
        logger.exception("فشل توليد درس %s", lesson_id)
        with get_connection() as conn:
            conn.execute(
                "UPDATE book_lessons SET status = 'failed', error = ?, "
                "updated_at = datetime('now') WHERE id = ?",
                (str(e)[:300], lesson_id),
            )
            conn.commit()
        raise


async def _generate_lesson_impl(
    llm: BaseLLM,
    lesson_id: int,
    grade_level: str,
    temperature: float | None,
    max_tokens: int | None,
) -> dict:
    """جسم التوليد الفعلي (يُفترض أن الحالة 'generating' قد سُجّلت قبلها)."""
    lesson = get_lesson(lesson_id)
    if lesson is None:
        raise ValueError(f"الدرس غير موجود (lesson_id={lesson_id})")
    # سياق الدرس: عنوان الوحدة + عنوان الدرس + نص المقطع (محدود بالحرف).
    # نجتز من موضع العنوان الظاهر في المحتوى — fallback: بداية المحتوى.
    content = get_book_content(lesson["book_id"])
    start = content.find(lesson["title"])
    start = start if start != -1 else 0
    segment = content[start : start + 12_000]

    prompt = (
        f"عنوان الوحدة: {lesson['unit_title'] or '—'}\n"
        f"عنوان الدرس: {lesson['title']}\n"
        f"مستوى الطالب: {grade_level}\n"
        "مقطع الكتاب:\n"
        "----------------\n"
        f"{segment or '(مقطع فارغ — اطلب من المستخدم التحقق من استخراج النص)'}\n"
        "----------------\n"
    )

    out = await llm.chat(
        [
            {"role": "system", "content": GENERATE_SYSTEM.format(grade=grade_level)},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature if temperature is not None else 0.7,
        max_tokens=max_tokens or 4096,
    )
    try:
        data = _extract_json(out)
    except ValueError:
        # محاولة خفيفة ثانية بطلب «JSON فقط» — بلا تغيير درجة حرارة ثقيل
        out2 = await llm.chat(
            [
                {
                    "role": "system",
                    "content": GENERATE_SYSTEM.format(grade=grade_level),
                },
                {
                    "role": "user",
                    "content": prompt
                    + "\n\nمهم: أعد فقط كائن JSON صالحاً، بلا أي شرح أو علامات ترميز.",
                },
            ],
            temperature=0.3,
            max_tokens=max_tokens or 4096,
        )
        data = _extract_json(out2)
    if not isinstance(data, dict) or "شرح" not in data:
        raise ValueError("الرد لم يحتوِ على شرح صالح")

    questions = data.get("أسئلة", [])
    exercises = data.get("تدريب", [])
    glossary = data.get("مصطلحات", [])
    title = data.get("title") or lesson["title"]

    with get_connection() as conn:
        conn.execute(
            "UPDATE book_lessons SET title = ?, content = ?, questions = ?, "
            "exercises = ?, glossary = ?, status = 'ready', error = '', "
            "updated_at = datetime('now') WHERE id = ?",
            (
                title,
                data["شرح"],
                json.dumps(questions, ensure_ascii=False),
                json.dumps(exercises, ensure_ascii=False),
                json.dumps(glossary, ensure_ascii=False),
                lesson_id,
            ),
        )
        conn.commit()
    # P2-26/28: حفظ ملفات معزولة + مزامنة بنك الأسئلة (لا يوقفان النجاح عند الفشل)
    try:
        persist_lesson_files(lesson_id)
        sync_quiz_bank(lesson_id)
    except Exception:
        logger.exception("فشل الحفظ المعزول/بنك الأسئلة للدرس %s", lesson_id)
    return {"id": lesson_id, "title": title}


async def generate_lessons(
    llm: BaseLLM,
    book_id: int,
    req: GenerateRequest,
) -> dict:
    """يولّد مجموعة دروس (أو كلها) بالتسلسل — الدرس الفاشل لا يوقف البقية (P2-22)."""
    lessons = list_lessons(book_id)
    if req.lesson_ids:
        wanted = set(req.lesson_ids)
        lessons = [lesson for lesson in lessons if lesson["id"] in wanted]
    if not lessons:
        return {"generated": [], "failed": []}

    set_book_status(book_id, "generating")
    generated: list[int] = []
    failed: list[dict] = []
    try:
        for lesson in lessons:
            try:
                await generate_lesson(
                    llm, lesson["id"], req.grade_level, req.temperature, req.max_tokens
                )
                generated.append(lesson["id"])
            except Exception as e:  # درس فاشل → سجّل وتابع
                logger.exception("فشل توليد درس %s", lesson["id"])
                failed.append({"lesson_id": lesson["id"], "error": str(e)[:300]})
                with get_connection() as conn:
                    conn.execute(
                        "UPDATE book_lessons SET status = 'failed', error = ?, "
                        "updated_at = datetime('now') WHERE id = ?",
                        (str(e)[:300], lesson["id"]),
                    )
                    conn.commit()
    finally:
        set_book_status(book_id, "ready" if generated and not failed else "analyzed")
    # P2-64: سجل النشاط — كل درس مكتمل يُسجّل كأنشطة
    for lesson_id in generated:
        log_study_activity(book_id, lesson_id, activity="lesson")
    return {"generated": generated, "failed": failed}


# ----------------------- فهرسة في RAG (P2-27) -----------------------


async def index_lesson_to_rag(lesson_id: int, engine) -> bool:
    """يفهرس نص شرح الدرس في RAG (كتاب → مادة استرجاع) — فشل صامت لا يكسر التوليد."""
    try:
        lesson = get_lesson(lesson_id)
        if not lesson or not lesson["content"].strip():
            return False
        from app.core.db import get_connection as conn_get

        with conn_get() as conn:
            cur = conn.execute(
                "INSERT INTO documents (filename, file_type, content) VALUES (?, 'lesson', ?)",
                (f"درس-{lesson['book_id']}-{lesson_id}.md", lesson["content"]),
            )
            doc_id = cur.lastrowid
            conn.commit()
        res = await engine.index_document(
            doc_id,
            f"درس-{lesson['book_id']}-{lesson_id}.md",
            lesson["content"],
        )
        return bool(res)
    except Exception:
        logger.exception("فشل فهرسة الدرس %s في RAG", lesson_id)
        return False


# ----------------------- بنك الأسئلة (P2-28) -----------------------


def _lesson_files_path(lesson: dict) -> Path | None:
    """مساحة معزولة للدرس (P2-26): data/books/<book_id>/<unit>/<lesson>/.

    يُعيد None إن تعذّر الإنشاء (بيئة قابلة للقراءة فقط) — الحفظ في القاعدة لا يتأثر.
    """
    try:
        book_id = lesson["book_id"]
        unit = str(lesson.get("unit_index") or 0)
        safe_title = re.sub(r"[^\w\s-]", "", str(lesson["title"]))[:60].strip() or "درس"
        base = Path(get_settings().data_dir) / "books" / str(book_id) / unit / safe_title
        base.mkdir(parents=True, exist_ok=True)
        return base
    except Exception:
        logger.exception("فشل إنشاء مساحة الدروس المعزولة")
        return None


def persist_lesson_files(lesson_id: int) -> bool:
    """يكتب شرح.md / أسئلة.md / تدريب.md على القرص (P2-26) — فشل صامت."""
    try:
        lesson = get_lesson(lesson_id)
        if not lesson or not lesson["content"].strip():
            return False
        folder = _lesson_files_path(lesson)
        if folder is None:
            return False
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "شرح.md").write_text(lesson["content"], encoding="utf-8")
        questions = lesson.get("questions") or []
        if isinstance(questions, str):
            questions = json.loads(questions or "[]")
        q_lines = [f"## سؤال {i + 1}\n{q.get('question', '')}" for i, q in enumerate(questions)]
        (folder / "أسئلة.md").write_text("\n\n".join(q_lines), encoding="utf-8")
        exercises = lesson.get("exercises") or []
        if isinstance(exercises, str):
            exercises = json.loads(exercises or "[]")
        e_lines = [f"## تمرين {i + 1}\n{e.get('question', '')}" for i, e in enumerate(exercises)]
        (folder / "تدريب.md").write_text("\n\n".join(e_lines), encoding="utf-8")
        return True
    except Exception:
        logger.exception("فشل كتابة ملفات الدرس %s", lesson_id)
        return False


def sync_quiz_bank(lesson_id: int) -> int:
    """يحلّل أسئلة الدرس المولّدة إلى quiz_bank (P2-28) — يُعيد عدد الأسئلة المُدرجة."""
    lesson = get_lesson(lesson_id)
    if not lesson:
        return 0
    # get_lesson يفك questions تلقائياً (قائمة) — تسامح مع نص JSON أيضاً
    questions = lesson.get("questions") or []
    if isinstance(questions, str):
        try:
            questions = json.loads(questions or "[]")
        except json.JSONDecodeError:
            return 0
    if not questions:
        return 0
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM quiz_bank WHERE lesson_id = ?", (lesson_id,))
            rows = []
            for q in questions:
                qtype = q.get("type", "mcq")
                answer = q.get("answer")
                rows.append(
                    (
                        lesson["book_id"],
                        lesson_id,
                        qtype,
                        str(q.get("question", "")),
                        json.dumps(q.get("options", []), ensure_ascii=False),
                        json.dumps(answer, ensure_ascii=False),
                        str(q.get("explanation", "")),
                        f"درس {lesson['title']}",
                    )
                )
            conn.executemany(
                "INSERT INTO quiz_bank "
                "(book_id, lesson_id, qtype, question, options, answer, explanation, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
            conn.commit()
            return len(rows)
    except Exception:
        logger.exception("فشل مزامنة بنك الأسئلة للدرس %s", lesson_id)
        return 0


def list_quiz(book_id: int | None = None, lesson_id: int | None = None) -> list[dict]:
    """أسئلة بنك الأسئلة — مفلترة اختيارياً بكتاب أو درس (يغذّي محاكي الامتحان 17)."""
    sql = "SELECT * FROM quiz_bank WHERE 1=1"
    params: list = []
    if book_id is not None:
        sql += " AND book_id = ?"
        params.append(book_id)
    if lesson_id is not None:
        sql += " AND lesson_id = ?"
        params.append(lesson_id)
    sql += " ORDER BY id"
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_quiz(quiz_id: int) -> dict | None:
    """سؤال واحد من بنك الأسئلة."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM quiz_bank WHERE id = ?", (quiz_id,)).fetchone()
        return dict(row) if row else None


def _quiz_expected(row: dict) -> str:
    """الإجابة النموذجية كنص مقارن (P2-30): الرقم في MCQ يصبح نص الخيار الصحيح.

    truefalse: True/False أو "true"/"false" يصبحان «صحيح»/«خطأ» ليطابقا أزرار الواجهة.
    """
    try:
        answer = json.loads(row["answer"] or '""')
    except json.JSONDecodeError:
        answer = row["answer"]
    if row["qtype"] == "mcq" and isinstance(answer, int):
        try:
            options = json.loads(row["options"] or "[]")
            return str(options[answer]) if 0 <= answer < len(options) else str(answer)
        except json.JSONDecodeError:
            return str(answer)
    if row["qtype"] == "truefalse":
        if isinstance(answer, bool):
            return "صحيح" if answer else "خطأ"
        if isinstance(answer, str):
            if answer.strip().lower() == "true":
                return "صحيح"
            if answer.strip().lower() == "false":
                return "خطأ"
    return str(answer)


def record_attempt(quiz_id: int, answer: str, expected: str) -> dict:
    """يسجّل محاولة إجابة (P2-30) ويُعيد نتيجة تصحيح بسيطة.

    يُطبَّع «true/false» من أزرار الواجهة إلى «صحيح/خطأ» ليطابق التوقع.
    """
    a = answer.strip()
    if a.lower() in ("true", "صحيح"):
        a = "صحيح"
    elif a.lower() in ("false", "خطأ"):
        a = "خطأ"
    is_correct = a == expected.strip()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO quiz_attempts (quiz_id, answer, is_correct) VALUES (?, ?, ?)",
            (quiz_id, answer, int(is_correct)),
        )
        conn.commit()
    return {"quiz_id": quiz_id, "is_correct": is_correct}


def book_progress(book_id: int) -> dict:
    """تقدّم مذاكرة كتاب (P2-30): مكتمل/إجمالي + نسبة الأسئلة الصحيحة."""
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM book_lessons WHERE book_id = ?", (book_id,)
        ).fetchone()["c"]
        done = conn.execute(
            "SELECT COUNT(*) AS c FROM book_lessons WHERE book_id = ? AND status = 'ready'",
            (book_id,),
        ).fetchone()["c"]
        quiz_ok = conn.execute(
            "SELECT COUNT(*) AS c FROM quiz_attempts a JOIN quiz_bank q ON a.quiz_id = q.id "
            "WHERE q.book_id = ? AND a.is_correct = 1",
            (book_id,),
        ).fetchone()["c"]
        quiz_total = conn.execute(
            "SELECT COUNT(*) AS c FROM quiz_attempts a JOIN quiz_bank q ON a.quiz_id = q.id "
            "WHERE q.book_id = ?",
            (book_id,),
        ).fetchone()["c"]
    return {
        "lessons_done": done,
        "lessons_total": total,
        "progress_pct": round(done / total * 100) if total else 0,
        "correct_answers": quiz_ok,
        "total_answers": quiz_total,
        "accuracy_pct": round(quiz_ok / quiz_total * 100) if quiz_total else 0,
    }


# ---------------------------------------------------------------------------
# P2-29: جلسة تدريب تفاعلية (في الذاكرة) — سؤال تلو الآخر مع تصحيح فوري
# ---------------------------------------------------------------------------

# جلسات التدريب النشطة: {token: {lesson_id, quiz_ids, index, correct, total}}
training_sessions: dict[str, dict] = {}


def start_training(lesson_id: int) -> dict:
    """يبدأ جلسة تدريب لدرس: يلتقط أسئلته من بنك الأسئلة (إن وُجد) ويعيد السؤال الأول."""
    quiz = list_quiz(lesson_id=lesson_id)
    token = f"tr-{lesson_id}-{len(training_sessions) + 1}-{__import__('time').time():.0f}"
    session = {
        "lesson_id": lesson_id,
        "quiz_ids": [q["id"] for q in quiz],
        "index": 0,
        "correct": 0,
        "total": len(quiz),
    }
    training_sessions[token] = session
    first = get_quiz(session["quiz_ids"][0]) if session["quiz_ids"] else None
    return {"token": token, "question": first, "index": 0, "total": session["total"]}


def submit_training_answer(token: str, answer: str) -> dict:
    """يصحّح إجابة المستخدم الحالية ويعيد التالي أو الملخص النهائي."""
    session = training_sessions.get(token)
    if session is None:
        return {"error": "جلسة تدريب غير موجودة أو انتهت"}
    quiz_ids = session["quiz_ids"]
    if session["index"] >= len(quiz_ids):
        return _training_summary(session)
    q = get_quiz(quiz_ids[session["index"]])
    expected = _quiz_expected(q)
    result = record_attempt(q["id"], answer, expected)
    if result["is_correct"]:
        session["correct"] += 1
    session["index"] += 1
    if session["index"] >= len(quiz_ids):
        return _training_summary(session)
    nxt = get_quiz(quiz_ids[session["index"]])
    return {
        "token": token,
        "result": result,
        "question": nxt,
        "index": session["index"],
        "total": session["total"],
        "correct": session["correct"],
    }


def _training_summary(session: dict) -> dict:
    """ملخص نهاية الجلسة + حذفها من الذاكرة."""
    summary = {
        "token": None,
        "done": True,
        "correct": session["correct"],
        "total": session["total"],
        "accuracy_pct": (
            round(session["correct"] / session["total"] * 100) if session["total"] else 0
        ),
    }
    for k in list(training_sessions):
        if training_sessions[k] is session:
            del training_sessions[k]
    return summary


# ---------------------------------------------------------------------------
# P2-131: تصدير/استيراد بنك أسئلة JSON موحد (تبادل بين المستخدمين)
# ---------------------------------------------------------------------------


def export_quiz_json(book_id: int | None = None) -> list[dict]:
    """يُصدّر بنك الأسئلة (كتاب كامل أو الكل) كقائمة JSON نظيفة قابلة للاستيراد."""
    rows = list_quiz(book_id=book_id)
    out = []
    for r in rows:
        try:
            options = json.loads(r["options"] or "[]")
        except json.JSONDecodeError:
            options = []
        try:
            answer = json.loads(r["answer"] or '""')
        except json.JSONDecodeError:
            answer = r["answer"]
        out.append(
            {
                "qtype": r["qtype"],
                "question": r["question"],
                "options": options,
                "answer": answer,
                "explanation": r["explanation"],
            }
        )
    return out


def import_quiz_json(book_id: int, lesson_id: int | None, items: list[dict]) -> int:
    """يستورد أسئلة JSON إلى بنك كتاب/درس — يُعيد عدد المُدخَلة.

    القائمة مرنة: تعمل على صيغة التصدير نفسها (qtype/question/options/answer)
    وعلى صيغ الدرس الخام (type بدل qtype).
    """
    if get_book(book_id) is None:
        raise ValueError("الكتاب غير موجود")
    inserted = 0
    with get_connection() as conn:
        for item in items:
            qtype = item.get("qtype") or item.get("type") or "mcq"
            question = str(item.get("question", "")).strip()
            if not question:
                continue
            options = item.get("options") or []
            answer = item.get("answer", "")
            conn.execute(
                "INSERT INTO quiz_bank (book_id, lesson_id, qtype, question, "
                "options, answer, explanation, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    book_id,
                    lesson_id,
                    qtype,
                    question,
                    json.dumps(options, ensure_ascii=False),
                    json.dumps(answer, ensure_ascii=False),
                    str(item.get("explanation", "")),
                    "import",
                ),
            )
            inserted += 1
        conn.commit()
    return inserted


# ---------------------------------------------------------------------------
# P2-77: بحث نصي سريع في الدروس المولّدة (SQLite LIKE + ترتيب)
# ---------------------------------------------------------------------------


def search_lessons(query: str, book_id: int | None = None, limit: int = 20) -> list[dict]:
    """بحث نصي خفيف في عناوين ومحتوى الدروس المولّدة (P2-77).

    يبحث في العنوان + الشرح + الأسئلة JSON — يعيد مقتطفات مع تمييز المطابقة.
    """
    q = (query or "").strip()
    if not q:
        return []
    like = f"%{q}%"
    sql = (
        "SELECT id, book_id, unit_index, unit_title, title, status, content "
        "FROM book_lessons WHERE status = 'ready' AND (title LIKE ? OR content LIKE ?"
        " OR questions LIKE ? OR glossary LIKE ?)"
    )
    params: list = [like, like, like, like]
    if book_id is not None:
        sql += " AND book_id = ?"
        params.append(book_id)
    sql += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    results = []
    for r in rows:
        content = r["content"] or ""
        idx = content.find(q)
        snippet = content[max(0, idx - 80) : idx + 160] if idx != -1 else content[:200]
        results.append(
            {
                "id": r["id"],
                "book_id": r["book_id"],
                "title": r["title"],
                "unit_title": r["unit_title"],
                "status": r["status"],
                "snippet": snippet.replace("\n", " ").strip(),
            }
        )
    return results


# ---------------------------------------------------------------------------
# P2-63: التعرف على كتب الوزارة (قوالب بنية موثقة)
# ---------------------------------------------------------------------------

MINISTRY_TEMPLATES: list[dict] = [
    {
        "key": "connect",
        "name": "Connect ( اللغة الإنجليزية )",
        "required_sections": ["Big picture", "Little words", "Grammar"],
        "unit_markers": ["Unit", "Lesson"],
    },
    {
        "key": "time_for_english",
        "name": "Time for English",
        "required_sections": ["Look and say", "Read", "Write"],
        "unit_markers": ["Lesson"],
    },
]


def detect_book_template(book_id: int) -> dict:
    """يحلّل محتوى الكتاب ويصنّفه بقالب وزاري مبني على العلامات (P2-63).

    إرجاع: {template_key, name, confidence} — confidence=0 إن غير مطابق.
    """
    content = (get_book_content(book_id) or "").lower()
    best: dict = {"template_key": "generic", "name": "عام", "confidence": 0.0}
    for tpl in MINISTRY_TEMPLATES:
        hits = sum(1 for s in tpl["required_sections"] if s.lower() in content)
        unit_hits = sum(1 for m in tpl["unit_markers"] if m.lower() in content)
        score = hits / max(1, len(tpl["required_sections"]))
        if unit_hits:
            score += 0.25
        if score > best["confidence"]:
            best = {
                "template_key": tpl["key"],
                "name": tpl["name"],
                "confidence": round(score, 2),
            }
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO book_templates (book_id, template_key) VALUES (?, ?)",
            (book_id, best["template_key"]),
        )
        conn.commit()
    return best


# ---------------------------------------------------------------------------
# P2-64: تقرير ولي الأمر — نشاط أسبوعي + تقدم + أخطاء
# ---------------------------------------------------------------------------


def log_study_activity(book_id: int, lesson_id: int | None, activity: str = "lesson") -> int:
    """يسجّل نشاطاً دراسياً (P2-64) — يُستدعى بعد إكمال درس/امتحان."""
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO study_activity (book_id, lesson_id, activity) VALUES (?, ?, ?)",
            (book_id, lesson_id, activity),
        )
        conn.commit()
        return cur.lastrowid


def guardian_report(book_id: int, days: int = 7) -> dict:
    """ملخص أسبوعي لولي الأمر (P2-64): دروس مكتملة، متوسط الأسئلة، نقاط الضعف."""
    progress = book_progress(book_id)
    with get_connection() as conn:
        since = f"datetime('now', '-{days} day')"
        activities = conn.execute(
            f"SELECT activity, COUNT(*) AS c FROM study_activity "
            f"WHERE book_id = ? AND created_at >= {since} "
            f"GROUP BY activity",
            (book_id,),
        ).fetchall()
        attempts = conn.execute(
            f"SELECT q.qtype, a.is_correct FROM quiz_attempts a "
            f"JOIN quiz_bank q ON a.quiz_id = q.id WHERE q.book_id = ? "
            f"AND a.created_at >= {since}",
            (book_id,),
        ).fetchall()
    by_type: dict[str, list] = {}
    for row in attempts:
        by_type.setdefault(row["qtype"], []).append(bool(row["is_correct"]))
    weak = [
        qtype
        for qtype, results in by_type.items()
        if len(results) >= 3 and sum(results) / len(results) < 0.6
    ]
    return {
        "period_days": days,
        "progress": progress,
        "weekly_activity": {r["activity"]: r["c"] for r in activities},
        "accuracy_by_qtype": {
            qt: (
                {
                    "correct": sum(v),
                    "total": len(v),
                    "pct": round(sum(v) / len(v) * 100),
                }
                if v
                else {"correct": 0, "total": 0, "pct": 0}
            )
            for qt, v in by_type.items()
        },
        "weak_points": weak,
    }


# ---------------------------------------------------------------------------
# P2-65: ركن الأزهر — تعريفات مواد/تقسيمات أزهرية
# ---------------------------------------------------------------------------

AL_AZHAR_SUBJECTS: dict[str, dict] = {
    "رياضيات بكالوريوس": {
        "division": "علوم إنسانية",
        "typical_books": ["تفاضيل", "تكامل", "مصفوفات", "جذور", "تفاضح"],
        "suggested_template": "connect",
    },
    "علوم بكالوريوس": {
        "division": "علوم إنسانية",
        "typical_books": ["أحياء", "كيمياء", "فيزياء", "جيولوجيا"],
        "suggested_template": "generic",
    },
    "لغة إنجليزية": {"division": "آداب", "suggested_template": "time_for_english"},
    "عربي": {"division": "آداب", "suggested_template": "generic"},
}


def al_azhar_profile(title: str) -> dict | None:
    """يحاول تطابق عنوان كتاب مع مادة أزهرية (P2-65) — بلا تغيير على DB."""
    t = (title or "").lower()
    for subject, info in AL_AZHAR_SUBJECTS.items():
        for book in info.get("typical_books", []):
            if book in t:
                return {"subject": subject, **info}
    return None
