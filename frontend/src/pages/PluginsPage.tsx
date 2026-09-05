import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import {
  disablePlugin,
  enablePlugin,
  fetchPlugins,
  generatePluginReport,
  indexPluginForRag,
  invokePlugin,
  type GeneratedReport,
} from "../lib/api";
import { errMsg } from "../lib/utils";

const STATUS_LABEL: Record<string, string> = {
  detected: "مكتشفة",
  validated: "تم التحقق",
  loaded: "محملة",
  enabled: "مفعّلة",
  running: "تعمل الآن",
  disabled: "معطّلة",
  error: "خطأ",
};

export function PluginsPage() {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [result, setResult] = useState<string>("");
  const [grades, setGrades] = useState("");
  const [reportTopic, setReportTopic] = useState("");
  const [report, setReport] = useState<GeneratedReport | null>(null);

  // React Query — تحميل القائمة مع كاش (P4-240)
  const qc = useQuery({
    queryKey: ["plugins"],
    queryFn: fetchPlugins,
    staleTime: 1000 * 60 * 2,
    retry: 2,
  });

  const plugins = qc.data ?? [];

  useEffect(() => {
    if (qc.isError) setError(errMsg(qc.error));
  }, [qc.isError, qc.error]);

  const invalidate = () => qc.refetch();

  const act = async (name: string, fn: () => Promise<unknown>) => {
    setBusy(name);
    setError("");
    try {
      await fn();
      await invalidate();
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setBusy("");
    }
  };

  const runGrades = async () => {
    setBusy("grades-tool");
    setResult("");
    try {
      const list = grades
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
        .map((g) => ({ subject: "مادة", grade: Number(g) }));
      const r = (await invokePlugin("grades-tool", { grades: list })) as {
        result: { average: number; count: number; max: number };
      };
      setResult(
        `المعدل: ${r.result.average} (من ${r.result.count} مادة، الأعلى ${r.result.max})`,
      );
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setBusy("");
    }
  };

  const downloadReport = (r: GeneratedReport) => {
    const blob = new Blob([r.markdown], {
      type: "text/markdown;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `تقرير-${r.topic}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div dir="rtl" className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-4xl p-6">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold">الإضافات</h1>
          <div className="flex gap-2">
            <Link
              to="/"
              className="rounded-lg bg-slate-200 px-4 py-2 text-sm hover:bg-slate-300"
            >
              المحادثة
            </Link>
            <Link
              to="/documents"
              className="rounded-lg bg-slate-200 px-4 py-2 text-sm hover:bg-slate-300"
            >
              مستنداتي
            </Link>
            <Link
              to="/plugins"
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
            >
              الإضافات
            </Link>
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-100 p-3 text-sm text-red-800">
            {error}
          </div>
        )}

        <div className="space-y-3">
          {plugins.map((p) => (
            <div
              key={p.name}
              className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="font-semibold">{p.title}</h2>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                      {p.type} · v{p.version}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-slate-600">{p.description}</p>
                  {p.last_error && (
                    <p className="mt-1 text-xs text-red-600">{p.last_error}</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-medium ${
                      p.status === "enabled" || p.status === "running"
                        ? "bg-green-100 text-green-800"
                        : p.status === "error"
                          ? "bg-red-100 text-red-800"
                          : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {STATUS_LABEL[p.status] ?? p.status}
                  </span>
                  <button
                    disabled={busy === p.name}
                    onClick={() =>
                      act(
                        p.name,
                        p.status === "enabled" || p.status === "running"
                          ? () => disablePlugin(p.name)
                          : () => enablePlugin(p.name),
                      )
                    }
                    className="rounded-lg border border-slate-300 px-3 py-1 text-sm hover:bg-slate-50 disabled:opacity-50"
                  >
                    {p.status === "enabled" || p.status === "running"
                      ? "تعطيل"
                      : "تفعيل"}
                  </button>
                  {p.type === "ui-page" && (
                    <Link
                      to={`/plugins/${p.name}`}
                      className="rounded-lg border border-green-300 px-3 py-1 text-sm text-green-700 hover:bg-green-50"
                    >
                      افتح الصفحة
                    </Link>
                  )}
                </div>
              </div>

              {p.name === "grades-tool" && (
                <div className="mt-3 rounded-lg bg-slate-50 p-3">
                  <div className="flex gap-2">
                    <input
                      value={grades}
                      onChange={(e) => setGrades(e.target.value)}
                      placeholder="درجات مفصولة بفواصل، مثال: 80,90,75"
                      className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
                    />
                    <button
                      onClick={runGrades}
                      disabled={busy === "grades-tool"}
                      className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                      احسب
                    </button>
                  </div>
                  {result && (
                    <p className="mt-2 text-sm font-medium text-green-800">
                      {result}
                    </p>
                  )}
                </div>
              )}

              {p.name === "books" && (
                <div className="mt-3 flex items-center justify-between rounded-lg bg-slate-50 p-3">
                  <p className="text-sm text-slate-600">
                    اربط كتب المكتبة بخط «اسأل كتابك» (RAG)
                  </p>
                  <button
                    onClick={() =>
                      act("books", async () => {
                        const r = await indexPluginForRag("books");
                        setResult(
                          r.indexed &&
                            Array.isArray(r.indexed) &&
                            r.indexed.length
                            ? `فُهرست ${r.indexed.length} كتب في RAG`
                            : "لا كتب بعد — أضف كتباً أولاً",
                        );
                      })
                    }
                    disabled={busy === "books"}
                    className="rounded-lg bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700 disabled:opacity-50"
                  >
                    فهرسة في RAG
                  </button>
                </div>
              )}

              {p.name === "reports" && (
                <div className="mt-3 rounded-lg bg-slate-50 p-3">
                  <div className="flex gap-2">
                    <input
                      value={reportTopic}
                      onChange={(e) => setReportTopic(e.target.value)}
                      placeholder="موضوع التقرير، مثال: التفاضل والتكامل"
                      className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
                    />
                    <button
                      onClick={async () => {
                        setBusy("reports");
                        setReport(null);
                        setError("");
                        try {
                          setReport(
                            await generatePluginReport(
                              "reports",
                              reportTopic.trim(),
                            ),
                          );
                        } catch (e) {
                          setError(errMsg(e));
                        } finally {
                          setBusy("");
                        }
                      }}
                      disabled={busy === "reports" || !reportTopic.trim()}
                      className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                      توليد تقرير
                    </button>
                  </div>
                  {report && (
                    <div className="mt-3">
                      <div className="mb-2 flex items-center justify-between">
                        <p className="text-sm font-medium text-green-800">
                          أُنشئ التقرير من {report.sources.length} مصدر — #ID{" "}
                          {report.report_ident}
                        </p>
                        <button
                          onClick={() => downloadReport(report)}
                          className="rounded-lg border border-green-300 px-3 py-1 text-sm text-green-700 hover:bg-green-50"
                        >
                          تنزيل Markdown
                        </button>
                      </div>
                      <pre
                        dir="rtl"
                        className="max-h-80 overflow-auto whitespace-pre-wrap rounded-lg border border-slate-200 bg-white p-3 text-sm"
                      >
                        {report.markdown}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
