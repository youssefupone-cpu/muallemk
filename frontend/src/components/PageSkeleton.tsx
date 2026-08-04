/**
 * مكوّن شريط تحميل بسيط — يُستخدم في Suspense fallback
 * لمنع إظهار صفحة فارغة أثناء تحميل الـ chunk.
 */
export function PageSkeleton() {
  return (
    <div
      aria-label="جارٍ التحميل…"
      className="flex h-screen items-center justify-center bg-slate-100"
    >
      <div className="flex items-center gap-3 text-slate-500">
        <svg
          className="-rotate-90 h-5 w-5 animate-spin"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
        <span className="text-sm">جارٍ التحميل…</span>
      </div>
    </div>
  );
}
