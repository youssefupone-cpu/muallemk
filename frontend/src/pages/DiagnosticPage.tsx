import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { AppLayout } from "../components/layout/AppLayout";
import {
  fetchBooks,
  fetchQuiz,
  submitQuizAttempt,
  type QuizBankItem,
} from "../lib/api";
import { errMsg } from "../lib/utils";

interface Row {
  item: QuizBankItem;
  userAnswer: string;
  isCorrect: boolean;
}

const DIAGNOSTIC_COUNT = 6;

function expectedText(item: QuizBankItem): string {
  if (item.qtype === "mcq") {
    try {
      const opts = JSON.parse(item.options || "[]") as string[];
      const idx = Number(item.answer);
      if (Array.isArray(opts) && opts[idx]) return opts[idx];
    } catch {
      /* تجاهل */
    }
  }
  return item.answer;
}

export default function DiagnosticPage() {
  const [bookId, setBookId] = useState<number | "">("");
  const [rows, setRows] = useState<Row[]>([]);
  const [idx, setIdx] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  // React Query — تحميل القوائم (P4-240)
  const qc = useQuery({
    queryKey: ["books"],
    queryFn: fetchBooks,
    staleTime: 1000 * 60 * 2,
    retry: 1,
  });

  const books = qc.data ?? [];
  useEffect(() => {
    if (qc.isError) setError(errMsg(qc.error));
  }, [qc.isError, qc.error]);

  const start = async () => {
    if (!bookId) return;
    setBusy(true);
    setError("");
    try {
      const quiz = await fetchQuiz(bookId);
      if (quiz.length === 0) {
        setError("لا توجد أسئلة — ولّد دروس الكتاب أولاً");
        setBusy(false);
        return;
      }
      setRows(
        quiz.slice(0, DIAGNOSTIC_COUNT).map((item) => ({
          item,
          userAnswer: "",
          isCorrect: false,
        })),
      );
      setIdx(0);
      setDone(false);
      setBusy(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  };

  const answer = async (value: string) => {
    if (busy || !rows[idx]) return;
    setBusy(true);
    try {
      const res = await submitQuizAttempt(rows[idx].item.id, value);
      const next = rows.map((r, i) =>
        i === idx ? { ...r, userAnswer: value, isCorrect: res.is_correct } : r,
      );
      setRows(next);
      if (idx + 1 >= rows.length) setDone(true);
      else setIdx(idx + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const correct = rows.filter((r) => r.isCorrect).length;
  const pct = rows.length ? Math.round((correct / rows.length) * 100) : 0;
  const level = pct >= 80 ? "متقدم" : pct >= 50 ? "متوسط" : "مبتدئ";

  const q = rows[idx]?.item;

  return (
    <AppLayout>
      <div className="mx-auto max-w-3xl px-4 py-6">
        <h1 className="mb-4 text-xl font-bold">اختبار تشخيصي سريع</h1>
        <p className="mb-4 text-sm text-slate-500">
          {DIAGNOSTIC_COUNT} أسئلة سريعة تقدّر مستواك (مبتدئ/متوسط/متقدم) لتخصيص
          درجة شرح الدروس.
        </p>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {rows.length === 0 && (
          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <label className="mb-2 block text-sm font-medium text-slate-700">
              اختر كتاباً
            </label>
            <select
              value={bookId}
              onChange={(e) =>
                setBookId(e.target.value ? Number(e.target.value) : "")
              }
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
            >
              <option value="">— اختر —</option>
              {books.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.title || b.filename}
                </option>
              ))}
            </select>
            <button
              onClick={() => void start()}
              disabled={!bookId || busy}
              className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {busy ? "جارٍ التحميل…" : "ابدأ التشخيص"}
            </button>
          </div>
        )}

        {rows.length > 0 && !done && q && (
          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <div className="mb-4 text-sm font-medium text-slate-500">
              السؤال {idx + 1} من {rows.length}
            </div>
            <h2 className="mb-4 text-lg font-medium">{q.question}</h2>

            {q.qtype === "mcq" && (
              <div className="space-y-2">
                {(() => {
                  try {
                    const opts = JSON.parse(q.options || "[]") as string[];
                    return opts.map((opt, i) => (
                      <button
                        key={i}
                        onClick={() => void answer(opt)}
                        disabled={busy}
                        className="block w-full rounded-lg border border-slate-300 px-4 py-2 text-right hover:border-blue-500 hover:bg-blue-50 disabled:opacity-50"
                      >
                        {opt}
                      </button>
                    ));
                  } catch {
                    return null;
                  }
                })()}
              </div>
            )}
            {q.qtype === "truefalse" && (
              <div className="flex gap-2">
                <button
                  onClick={() => void answer("true")}
                  disabled={busy}
                  className="rounded-lg border border-green-300 px-6 py-2 hover:bg-green-50 disabled:opacity-50"
                >
                  صحيح
                </button>
                <button
                  onClick={() => void answer("false")}
                  disabled={busy}
                  className="rounded-lg border border-red-300 px-6 py-2 hover:bg-red-50 disabled:opacity-50"
                >
                  خطأ
                </button>
              </div>
            )}
            {(q.qtype === "fill" || q.qtype === "essay") && (
              <form
                className="flex gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  const input = e.currentTarget.elements.namedItem(
                    "answer",
                  ) as HTMLInputElement;
                  void answer(input.value);
                }}
              >
                <input
                  name="answer"
                  placeholder="اكتب إجابتك…"
                  className="flex-1 rounded-lg border border-slate-300 px-3 py-2"
                />
                <button
                  type="submit"
                  disabled={busy}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  التالي
                </button>
              </form>
            )}
          </div>
        )}

        {done && (
          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="mb-2 text-lg font-bold">
              نتيجتك: مستوى {level} ({correct}/{rows.length} — {pct}%)
            </h2>
            <p className="mb-4 text-sm text-slate-500">
              {level === "متقدم"
                ? "ممتاز — يمكن توليد الدروس بمستوى متقدم."
                : level === "متوسط"
                  ? "جيد — سنولّد الدروس بمستوى متوسط مع تدريبات مكثفة."
                  : "لا بأس — سنبدأ بمستوى مبتدئ مع شرح مبسط وتدريبات خطوة بخطوة."}
            </p>
            <ul className="mb-4 space-y-2">
              {rows.map((r, i) => (
                <li
                  key={r.item.id}
                  className={`rounded-lg border p-3 text-sm ${
                    r.isCorrect
                      ? "border-green-200 bg-green-50"
                      : "border-red-200 bg-red-50"
                  }`}
                >
                  <span className="font-medium">
                    {i + 1}. {r.item.question}
                  </span>
                  {!r.isCorrect && (
                    <div className="mt-1 text-slate-600">
                      الصحيح: {expectedText(r.item)}
                    </div>
                  )}
                </li>
              ))}
            </ul>
            <button
              onClick={() => {
                setRows([]);
                setDone(false);
                setError("");
              }}
              className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
            >
              إعادة الاختبار
            </button>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
