import { Download } from "lucide-react";
import { useRegisterSW } from "virtual:pwa-register/react";

import { AppToaster } from "./AppToaster";

/**
 * ReloadPrompt — إشعار تحديث Service Worker + دونّ اتصال (P4-237).
 *
 * يظهر إشعاراً عندما يتوفّر تحديث للـ PWA (needRefresh) أو بعد التسجيل
 * الأولى (offlineReady = "المحتوى الآن متاح دون اتصال").
 */
export function ReloadPrompt() {
  const {
    offlineReady: [offlineReady, setOfflineReady],
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegistered(reg) {
      // تحديث دوري خلفي خفيف — كل 30 دقيقلاً
      if (reg) setInterval(() => reg.update(), 30 * 60 * 1000);
    },
  });

  const update = async () => {
    setNeedRefresh(false);
    setOfflineReady(false);
    await updateServiceWorker();
    window.location.reload();
  };

  // Use the centralized Toaster instead of inline toast so messages appear
  // in the same place as app notifications.
  return (
    <>
      <AppToaster />
      {(offlineReady || needRefresh) && (
        <button
          onClick={update}
          className="fixed bottom-4 start-4 z-50 flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm text-white shadow-lg hover:bg-blue-700"
        >
          <Download className="h-4 w-4" />
          {offlineReady
            ? "المحتوى متاح دون اتصال الآن"
            : "تحديث جديد متاح — اضغط لإعادة التحميل"}
        </button>
      )}
    </>
  );
}
