import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { AppLayout } from "../components/layout/AppLayout";
import {
  fetchBooks,
  fetchQuiz,
  submitQuizAttempt,
  type QuizBankItem,
} from "../lib/api";
import { errMsg } from "../lib/utils";

type Phase = "pick" | "quiz" | "done";

const EXAM_MINUTES = 30;
const Q_PER_EXAM = 10;

interface QA {
  item: QuizBankItem;
  userAnswer: string;
  isCorrect: boolean;
}

function expectedText(item: QuizBankItem): string {
  if (item.qtype === "mcq") {
    const idx = Number(item.answer);
    try {
      const opts = JSON.parse(item.options || "[]") as string[];
      if (Array.isArray(opts) && Number.isInteger(idx) && opts[idx]) {
        return opts[idx];
      }
    } catch {
      /* تجاهل — إرجاع الخام */
    }
    return item.answer;
  }
  return item.answer === "true"
    ? "صحيح"
    : item.answer === "false"
      ? "خطأ"
      : item.answer;
}

export default function ExamPage() {
  const [bookId, setBookId] = useState<number | "">("");
  const [phase, setPhase] = useState<Phase>("pick");
  const [qa, setQa] = useState<QA[]>([]);
  const [current, setCurrent] = useState(0);
  const [secondsLeft, setSecondsLeft] = useState(EXAM_MINUTES * 60);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const timerRef = useRef<number | null>(null);

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

  const startExam = useCallback(async () => {
    if (!bookId) return;
    setBusy(true);
    setError("");
    try {
      const quiz = await fetchQuiz(bookId);
      if (quiz.length === 0) {
        setError("لا توجد أسئلة في بنك الأسئلة — ولّد دروس الكتاب أولاً");
        setBusy(false);
        return;
      }
      const picked = quiz.slice(0, Q_PER_EXAM);
      setQa(
        picked.map((item) => ({
          item,
          userAnswer: "",
          isCorrect: false,
        })),
      );
      setCurrent(0);
      setSecondsLeft(EXAM_MINUTES * 60);
      setPhase("quiz");
      setBusy(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  }, [bookId]);

  // عدّاد زمن تنازلي
  useEffect(() => {
    if (phase !== "quiz") return;
    timerRef.current = window.setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          if (timerRef.current) window.clearInterval(timerRef.current);
          finishExam();
          return 0;
        }
        return s - 1;
      });
    }, 1000);
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  const pickAnswer = useCallback(
    async (answer: string) => {
      if (!qa[current] || busy) return;
      setBusy(true);
      const entry = qa[current];
      try {
        const res = await submitQuizAttempt(entry.item.id, answer);
        const updated = qa.map((x, i) =>
          i === current
            ? { ...x, userAnswer: answer, isCorrect: res.is_correct }
            : x,
        );
        setQa(updated);
        setCurrent((c) => c + 1);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    },
    [busy, current, qa],
  );

  const finishExam = useCallback(async () => {
    if (timerRef.current) window.clearInterval(timerRef.current);
    setPhase("done");
  }, []);

  const minutes = Math.floor(secondsLeft / 60);
  const secs = secondsLeft % 60;
  const doneCount = qa.filter((x) => x.userAnswer !== "").length;
  const correctCount = qa.filter((x) => x.isCorrect).length;

  const scorePercent = useMemo(
    () => (doneCount > 0 ? Math.round((correctCount / doneCount) * 100) : 0),
    [correctCount, doneCount],
  );

  const q = qa[current]?.item;

  return (
    <AppLayout>
      <div className="mx-auto max-w-3xl px-4 py-6">
        <h1 className="mb-4 text-xl font-bold">محاكي امتحان 2026</h1>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {phase === "pick" && (
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
            <p className="mt-3 text-sm text-slate-500">
              {Q_PER_EXAM} أسئلة من بنك الأسئلة — المدة {EXAM_MINUTES} دقيقة —
              تصحيح فوري فور اختيار كل إجابة.
            </p>
            <button
              onClick={startExam}
              disabled={!bookId || busy}
              className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {busy ? "جارٍ التحميل…" : "ابدأ الامتحان"}
            </button>
          </div>
        )}

        {phase === "quiz" && q && (
          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <div className="mb-4 flex items-center justify-between text-sm">
              <span className="font-medium text-slate-700">
                السؤال {current + 1} من {qa.length} — أُجيب {doneCount}
              </span>
              <span
                className={`rounded-lg px-3 py-1 font-mono ${
                  secondsLeft < 120
                    ? "bg-red-100 text-red-700"
                    : "bg-slate-100 text-slate-700"
                }`}
              >
                {minutes}:{secs.toString().padStart(2, "0")}
              </span>
            </div>

            <h2 className="mb-4 text-lg font-medium leading-relaxed">
              {q.question}
            </h2>

            {q.qtype === "mcq" && (
              <div className="space-y-2">
                {(() => {
                  try {
                    const opts = JSON.parse(q.options || "[]") as string[];
                    return opts.map((opt, i) => (
                      <button
                        key={i}
                        onClick={() => void pickAnswer(opt)}
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
                  onClick={() => void pickAnswer("true")}
                  disabled={busy}
                  className="rounded-lg border border-green-300 px-6 py-2 hover:bg-green-50 disabled:opacity-50"
                >
                  صحيح
                </button>
                <button
                  onClick={() => void pickAnswer("false")}
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
                  void pickAnswer(input.value);
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
                  أجب
                </button>
              </form>
            )}

            {current >= qa.length && (
              <button
                onClick={() => finishExam()}
                className="mt-4 rounded-lg bg-green-600 px-4 py-2 text-white hover:bg-green-700"
              >
                اعرض النتيجة
              </button>
            )}
          </div>
        )}

        {phase === "done" && (
          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="mb-2 text-lg font-bold">
              النتيجة: {correctCount}/{doneCount} صحيحة ({scorePercent}%)
            </h2>
            <p className="mb-4 text-sm text-slate-500">
              {scorePercent >= 85
                ? "ممتاز! جاهز للامتحان."
                : scorePercent >= 60
                  ? "جيد — راجع الدروس التي أخطأت فيها."
                  : "تحتاج مراجعة — أعد قراءة الدروس ثم جرّب مجدداً."}
            </p>
            <ul className="space-y-2">
              {qa.map((x, i) => (
                <li
                  key={x.item.id}
                  className={`rounded-lg border p-3 text-sm ${
                    x.isCorrect
                      ? "border-green-200 bg-green-50"
                      : "border-red-200 bg-red-50"
                  }`}
                >
                  <div className="font-medium">
                    {i + 1}. {x.item.question}
                  </div>
                  {!x.isCorrect && (
                    <div className="mt-1 text-slate-600">
                      الإجابة الصحيحة:{" "}
                      <span className="font-semibold">
                        {expectedText(x.item)}
                      </span>
                    </div>
                  )}
                </li>
              ))}
            </ul>
            <button
              onClick={() => {
                setPhase("pick");
                setQa([]);
                setError("");
              }}
              className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
            >
              امتحان جديد
            </button>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
