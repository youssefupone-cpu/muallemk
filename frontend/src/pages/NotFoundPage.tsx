import { Link } from "react-router-dom";

import { AppLayout } from "../components/layout/AppLayout";

export function NotFoundPage() {
  return (
    <AppLayout>
      <div className="mx-auto max-w-2xl px-6 py-16 text-center">
        <h1 className="mb-3 text-4xl font-bold text-slate-800">404</h1>
        <p className="mb-6 text-slate-600">
          الصفحة المطلوبة غير موجودة — ربما تمت حذفها أو لم تعد موجودة.
        </p>
        <Link
          to="/"
          className="inline-block rounded-lg bg-blue-600 px-5 py-2 text-white hover:bg-blue-700"
        >
          العودة للمحادثة
        </Link>
      </div>
    </AppLayout>
  );
}
