import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { errMsg } from "../lib/utils";

import { AppLayout } from "../components/layout/AppLayout";
import {
  analyzeBook,
  deleteBook,
  exportQuizJson,
  fetchBook,
  fetchBooks,
  fetchLesson,
  generateBookLessons,
  importQuizJson,
  regenerateLesson,
  searchLessons,
  uploadBook,
  type BookDetail,
  type BookLesson,
  type LessonContent,
} from "../lib/api";
import { loadSettings } from "../lib/settings";

interface LessonSearchHit {
  id: number;
  book_id: number;
  title: string;
  unit_title: string;
  snippet: string;
}

const STATUS_LABEL: Record<string, string> = {
  uploaded: "مرفوع — لم يُحلَّل",
  analyzed: "محلَّل — جاهز للتوليد",
  generating: "جارٍ التوليد…",
  ready: "جاهز",
  generated: "توليد جزئي",
};

function Flashcards({ lesson }: { lesson: LessonContent }) {
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const cards = useMemo(() => {
    const fromGlossary = lesson.glossary.map((g) => ({
      front: String(g.term ?? ""),
      back: String(g.definition ?? ""),
    }));
    const fromQuestions = lesson.questions.map((q) => ({
      front: String(q.question ?? ""),
      back: String(q.answer ?? ""),
    }));
    return [...fromGlossary, ...fromQuestions].filter((c) => c.front);
  }, [lesson]);
  if (cards.length === 0) return null;
  const card = cards[index % cards.length];
  return (
    <div className="mt-6">
      <h3 className="mb-2 text-lg font-bold">بطاقات مراجعة ({cards.length})</h3>
      <div
        className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-blue-200 bg-blue-50/50 px-4 py-8 text-center"
        onClick={() => setFlipped((f) => !f)}
        role="button"
        aria-label="اقلِب البطاقة"
      >
        <div className="text-sm text-slate-400">
          {flipped ? "الجواب" : "السؤال"} — اضغط للقلب
        </div>
        <div className="mt-2 text-lg font-medium leading-relaxed">
          {flipped ? card.back : card.front}
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between">
        <button
          onClick={() => {
            setIndex((i) => (i - 1 + cards.length) % cards.length);
            setFlipped(false);
          }}
          className="rounded-lg bg-slate-200 px-4 py-1.5 text-sm hover:bg-slate-300"
        >
          السابق
        </button>
        <span className="text-sm text-slate-500">
          {index + 1} / {cards.length}
        </span>
        <button
          onClick={() => {
            setIndex((i) => (i + 1) % cards.length);
            setFlipped(false);
          }}
          className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700"
        >
          التالي
        </button>
      </div>
    </div>
  );
}

function LessonView({
  lesson,
  onOpen,
  onGenerate,
  busy,
}: {
  lesson: BookLesson;
  onOpen: (id: number) => void;
  onGenerate: (id: number) => void;
  busy: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2">
      <button
        onClick={() => onOpen(lesson.id)}
        disabled={lesson.status !== "ready"}
        className="truncate text-right text-sm font-medium text-slate-700 hover:text-blue-600 disabled:cursor-not-allowed disabled:text-slate-400"
        title={
          lesson.status === "ready" ? "افتح الدرس" : "الدروس في انتظار التوليد"
        }
      >
        {lesson.title}
      </button>
      <div className="flex shrink-0 items-center gap-2">
        {lesson.status === "ready" && (
          <span className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-700">
            جاهز
          </span>
        )}
        {lesson.status === "failed" && (
          <span className="rounded bg-red-100 px-2 py-0.5 text-xs text-red-700">
            فشل
          </span>
        )}
        {lesson.status !== "ready" && (
          <button
            onClick={() => onGenerate(lesson.id)}
            disabled={busy}
            className="rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700 disabled:opacity-50"
          >
            توليد
          </button>
        )}
      </div>
    </div>
  );
}

function QuestionRenderer({ q, i }: { q: Record<string, unknown>; i: number }) {
  const typeLabel =
    {
      mcq: "اختيار من متعدد",
      true_false: "صح/خطأ",
      complete: "أكمل",
      essay: "مقالي",
    }[String(q.type)] ?? String(q.type);

  const options = Array.isArray(q.options) ? (q.options as string[]) : [];
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <p className="text-sm font-semibold">
        <span className="ml-1 rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-700">
          {typeLabel}
        </span>
        {i + 1}. {String(q.question)}
      </p>
      {options.length > 0 && (
        <ul className="mt-2 space-y-1 text-sm text-slate-700">
          {options.map((o, j) => (
            <li key={j}>
              {["أ", "ب", "ج", "د"][j] ?? j + 1}. {o}
            </li>
          ))}
        </ul>
      )}
      {q.answer !== undefined && (
        <p className="mt-2 text-xs text-green-700">
          الإجابة: {String(q.answer)}
          {q.explanation ? ` — ${String(q.explanation)}` : ""}
        </p>
      )}
    </div>
  );
}

function ExerciseRenderer({ e, i }: { e: Record<string, unknown>; i: number }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <p className="text-sm font-semibold">
        {i + 1}. {String(e.question)}
      </p>
      {e.hint ? (
        <p className="mt-1 text-xs text-amber-700">تلميح: {String(e.hint)}</p>
      ) : null}
      {e.answer ? (
        <p className="mt-1 text-xs text-green-700">الحل: {String(e.answer)}</p>
      ) : null}
    </div>
  );
}

export function BooksPage() {
  const [selected, setSelected] = useState<BookDetail | null>(null);
  const [lesson, setLesson] = useState<LessonContent | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [generating, setGenerating] = useState(false);
  const [searchQ, setSearchQ] = useState("");
  const [hits, setHits] = useState<LessonSearchHit[] | null>(null);
  const [importMsg, setImportMsg] = useState("");

  const settings = loadSettings();

  // React Query — تحميل القائمة مرة واحدة مع كاش (P4-240)
  const qc = useQuery({
    queryKey: ["books"],
    queryFn: fetchBooks,
    staleTime: 1000 * 60 * 2,
    retry: 2,
  });

  const books = qc.data ?? [];

  useEffect(() => {
    if (qc.isError) setError(errMsg(qc.error));
  }, [qc.isError, qc.error]);

  const invalidate = () => qc.refetch();

  const refreshSelected = async (id: number) => {
    try {
      setSelected(await fetchBook(id));
      setLesson(null);
    } catch (e) {
      setError(errMsg(e));
    }
  };

  const openBook = async (id: number) => {
    setError("");
    await refreshSelected(id);
  };

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setBusy("upload");
    setError("");
    try {
      const book = await uploadBook(f);
      await invalidate();
      await refreshSelected(book.id);
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setBusy("");
      e.target.value = "";
    }
  };

  const onAnalyze = async (id: number) => {
    setBusy("analyze");
    setError("");
    try {
      const lessons = await analyzeBook(id);
      if (lessons.length === 0)
        setError("لم يظهر أي درس — تأكد من جودة الكتاب");
      await invalidate();
      await refreshSelected(id);
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setBusy("");
    }
  };

  const onGenerate = async (id: number, lessonIds: number[] | null) => {
    setGenerating(true);
    setError("");
    try {
      const r = await generateBookLessons(id, lessonIds, settings);
      if (r.failed.length > 0) {
        setError(`فشل توليد ${r.failed.length} درس(اً)`);
      }
      await invalidate();
      await refreshSelected(id);
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setGenerating(false);
    }
  };

  const onOpenLesson = async (lessonId: number) => {
    setError("");
    try {
      setLesson(await fetchLesson(lessonId));
    } catch (err) {
      setError(errMsg(err));
    }
  };

  const onSearch = async (q: string) => {
    setSearchQ(q);
    if (!q.trim()) {
      setHits(null);
      return;
    }
    try {
      setHits(await searchLessons(q));
      setError("");
    } catch (err) {
      setError(errMsg(err));
      setHits(null);
    }
  };

  const onExportQuiz = async (id: number) => {
    try {
      const data = await exportQuizJson(id);
      const blob = new Blob([JSON.stringify(data.items, null, 2)], {
        type: "application/json",
      });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `quiz-${id}.json`;
      a.click();
      URL.revokeObjectURL(a.href);
      setImportMsg(`صُدِّر ${data.count} سؤالاً`);
    } catch (err) {
      setError(errMsg(err));
    }
  };

  const onImportQuiz = async (
    e: React.ChangeEvent<HTMLInputElement>,
    bookId: number,
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const items = JSON.parse(await file.text());
      const r = await importQuizJson(bookId, items);
      setImportMsg(`استُورد ${r.imported} سؤالاً`);
      setError("");
    } catch (err) {
      setError(errMsg(err));
    } finally {
      e.target.value = "";
    }
  };

  const onRegenerateLesson = async (lessonId: number) => {
    setGenerating(true);
    setError("");
    try {
      const r = await regenerateLesson(lessonId, settings);
      if (r.failed.length > 0)
        setError(`فشل إعادة التوليد: ${r.failed[0].error}`);
      else setImportMsg("أُعيد توليد الدرس بنجاح");
      await refreshSelected(selected?.book.id ?? 0);
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setGenerating(false);
    }
  };

  const onDeleteBook = async (id: number) => {
    if (!window.confirm("حذف الكتاب وجميع دروسه؟")) return;
    setError("");
    try {
      await deleteBook(id);
      setSelected(null);
      setLesson(null);
      await invalidate();
    } catch (err) {
      setError(errMsg(err));
    }
  };

  const pendingLessons =
    selected?.units
      .flatMap((u) => u.lessons)
      .filter((l) => l.status !== "ready") ?? [];

  return (
    <AppLayout>
      <div className="mx-auto max-w-5xl p-6">
        <h1 className="mb-6 text-2xl font-bold">مكتبة الكتب الذكية</h1>
        {error && (
          <div className="mb-4 rounded-lg bg-red-100 p-3 text-sm text-red-800">
            {error}
          </div>
        )}
        {importMsg && (
          <div className="mb-4 rounded-lg bg-emerald-100 p-3 text-sm text-emerald-800">
            {importMsg}
          </div>
        )}

        <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <label className="block text-sm font-medium text-slate-700">
            ارفع كتاباً (PDF / Word / EPUB / نص — حتى 100MB)
          </label>
          <input
            type="file"
            multiple={false}
            onChange={onUpload}
            disabled={busy === "upload"}
            className="mt-2 block w-full text-sm"
          />
          <p className="mt-1 text-xs text-slate-500">
            بعد الرفع اضغط «تحليل البنية» لاستخراج الوحدات والدروس، ثم «توليد
            الكل».
          </p>
        </div>

        <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <input
            type="search"
            value={searchQ}
            onChange={(e) => void onSearch(e.target.value)}
            placeholder="ابحث في الدروس المولّدة… (P2-77)"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          {hits && (
            <ul className="mt-3 space-y-2">
              {hits.length === 0 && (
                <li className="text-sm text-slate-500">لا نتائج مطابقة.</li>
              )}
              {hits.slice(0, 6).map((h) => (
                <li key={h.id}>
                  <button
                    onClick={() => void onOpenLesson(h.id)}
                    className="block w-full rounded-lg border border-slate-200 p-2 text-right text-sm hover:bg-slate-50"
                  >
                    <span className="font-medium text-blue-700">{h.title}</span>
                    <span className="mx-2 text-xs text-slate-400">
                      {h.unit_title}
                    </span>
                    <p className="mt-1 text-xs text-slate-500">{h.snippet}</p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <h2 className="mb-3 text-lg font-semibold">
              الكتب ({books.length})
            </h2>
            <div className="space-y-2">
              {books.length === 0 && (
                <p className="text-sm text-slate-500">
                  لا كتب بعد — ارفع كتابك الأول.
                </p>
              )}
              {books.map((b) => (
                <div
                  key={b.id}
                  className={`flex cursor-pointer items-center justify-between rounded-xl border p-3 shadow-sm transition ${
                    selected?.book.id === b.id
                      ? "border-blue-400 bg-blue-50"
                      : "border-slate-200 bg-white hover:border-blue-300"
                  }`}
                  onClick={() => openBook(b.id)}
                >
                  <div className="min-w-0">
                    <h3 className="truncate font-medium">{b.title}</h3>
                    <p className="text-xs text-slate-500">
                      {b.lesson_count} درس · {b.unit_count} وحدة ·{" "}
                      {STATUS_LABEL[b.status] ?? b.status}
                    </p>
                  </div>
                  <span className="shrink-0 text-xs text-slate-400">
                    {new Date(b.created_at).toLocaleDateString("ar")}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div>
            {selected ? (
              <div>
                <div className="mb-3 flex items-center justify-between">
                  <h2 className="text-lg font-semibold">
                    {selected.book.title}
                  </h2>
                  <div className="flex gap-2">
                    <button
                      onClick={() => void onExportQuiz(selected.book.id)}
                      className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm text-white hover:bg-emerald-700"
                    >
                      تصدير الأسئلة
                    </button>
                    <label className="cursor-pointer rounded-lg bg-emerald-100 px-3 py-1.5 text-sm text-emerald-700 hover:bg-emerald-200">
                      استيراد أسئلة
                      <input
                        type="file"
                        accept="application/json"
                        className="hidden"
                        onChange={(e) => void onImportQuiz(e, selected.book.id)}
                      />
                    </label>
                    <button
                      onClick={() => onAnalyze(selected.book.id)}
                      disabled={busy === "analyze" || generating}
                      className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {busy === "analyze" ? "يحلّل…" : "تحليل البنية"}
                    </button>
                    {pendingLessons.length > 0 && (
                      <button
                        onClick={() => onGenerate(selected.book.id, null)}
                        disabled={generating}
                        className="rounded-lg bg-green-600 px-3 py-1.5 text-sm text-white hover:bg-green-700 disabled:opacity-50"
                      >
                        {generating
                          ? "يولّد…"
                          : `توليد الكل (${pendingLessons.length})`}
                      </button>
                    )}
                    <button
                      onClick={() => onDeleteBook(selected.book.id)}
                      className="rounded-lg bg-red-100 px-3 py-1.5 text-sm text-red-700 hover:bg-red-200"
                    >
                      حذف
                    </button>
                  </div>
                </div>

                {selected.units.length === 0 ? (
                  <p className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
                    لم يُحلَّل بعد — اضغط «تحليل البنية».
                  </p>
                ) : (
                  <div className="max-h-[60vh] space-y-3 overflow-y-auto">
                    {selected.units.map((u) => (
                      <div
                        key={u.index}
                        className="rounded-xl border border-slate-200 bg-white p-3"
                      >
                        <h3 className="mb-2 font-semibold text-slate-700">
                          {u.title || "الكتاب"}
                        </h3>
                        <div className="space-y-1">
                          {u.lessons.map((l) => (
                            <LessonView
                              key={l.id}
                              lesson={l}
                              busy={generating}
                              onOpen={onOpenLesson}
                              onGenerate={(lid) =>
                                onGenerate(selected.book.id, [lid])
                              }
                            />
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
                اختر كتاباً لعرض بنيته ودروسه.
              </div>
            )}
          </div>
        </div>

        {lesson && (
          <div className="mt-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold">{lesson.title}</h2>
                <p className="text-sm text-slate-500">
                  {lesson.unit_title || "الكتاب"}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => void onRegenerateLesson(lesson.id)}
                  disabled={generating}
                  className="rounded-lg bg-amber-100 px-3 py-1.5 text-sm text-amber-700 hover:bg-amber-200 disabled:opacity-50"
                  title="إعادة توليد الشرح والأسئلة (P2-31)"
                >
                  {generating ? "يولّد…" : "إعادة التوليد"}
                </button>
                <button
                  onClick={() => setLesson(null)}
                  className="rounded-lg bg-slate-200 px-3 py-1.5 text-sm hover:bg-slate-300"
                >
                  إغلاق
                </button>
              </div>
            </div>

            <div className="whitespace-pre-wrap text-sm leading-8" dir="rtl">
              {lesson.content.split("\n").map((line, i) =>
                line.startsWith("## ") ? (
                  <h3 key={i} className="mt-4 text-lg font-bold text-slate-800">
                    {line.replace(/^##\s+/, "")}
                  </h3>
                ) : line.startsWith("# ") ? (
                  <h3 key={i} className="mt-4 text-lg font-bold text-slate-800">
                    {line.replace(/^#\s+/, "")}
                  </h3>
                ) : (
                  <p key={i} className="my-2">
                    {line || "\u00A0"}
                  </p>
                ),
              )}
            </div>

            {lesson.questions.length > 0 && (
              <div className="mt-6">
                <h3 className="mb-2 text-lg font-bold">
                  أسئلة ({lesson.questions.length})
                </h3>
                <div className="space-y-2">
                  {lesson.questions.map((q, i) => (
                    <QuestionRenderer
                      key={i}
                      q={q as unknown as Record<string, unknown>}
                      i={i}
                    />
                  ))}
                </div>
              </div>
            )}

            {lesson.exercises.length > 0 && (
              <div className="mt-6">
                <h3 className="mb-2 text-lg font-bold">تدريب</h3>
                <div className="space-y-2">
                  {lesson.exercises.map((e, i) => (
                    <ExerciseRenderer
                      key={i}
                      e={e as unknown as Record<string, unknown>}
                      i={i}
                    />
                  ))}
                </div>
              </div>
            )}

            {lesson.glossary.length > 0 && (
              <div className="mt-6">
                <h3 className="mb-2 text-lg font-bold">
                  قاموس المصطلحات ({lesson.glossary.length})
                </h3>
                <div className="grid gap-2 sm:grid-cols-2">
                  {lesson.glossary.map((g, i) => (
                    <div
                      key={i}
                      className="rounded-lg border border-blue-100 bg-blue-50/50 p-3"
                    >
                      <div className="font-semibold text-blue-700">
                        {String(g.term ?? "")}
                      </div>
                      <div className="mt-1 text-sm text-slate-600">
                        {String(g.definition ?? "")}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <Flashcards lesson={lesson} />
          </div>
        )}
      </div>
    </AppLayout>
  );
}
