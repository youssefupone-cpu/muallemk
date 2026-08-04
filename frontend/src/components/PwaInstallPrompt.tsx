import { useEffect, useState } from "react";

/**
 * PWA Install Prompt (P4-240)
 *
 * Chrome 125+ لم يعد يطلق beforeinstallprompt بشكل موثوق على الأصلات الإنتاجية
 * (تم توثيقه في problems/2026-08-04-pwa-install-banner.md).
 *
 * النهج المقترح:
 * 1. التقاط beforeinstallprompt وتأخيره → زر تثبيت يدوي.
 * 2. إظهار تعليمات "إضافة إلى الشريحة" يدوياً لأجهزة iOS/Safari.
 * 3. مراقبة display-mode: browser — لا تُظهر البانر إذا كانت مثبتة.
 */
export function PwaInstallPrompt() {
  const [deferred, setDeferred] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [show, setShow] = useState(false);
  const [isIOS, setIsIOS] = useState(false);

  useEffect(() => {
    // iOS لا يدعم beforeinstallprompt — نُظهر التعليمات اليدوية.
    const iOS =
      /iPad|iPhone|iPod/.test(navigator.userAgent) && !("MSStream" in window);
    setIsIOS(iOS);

    const onBeforeInstallPrompt = (e: BeforeInstallPromptEvent) => {
      e.preventDefault();
      setDeferred(e);
      setShow(true);
    };

    const onAppInstalled = () => {
      setShow(false);
      setDeferred(null);
    };

    window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt);
    window.addEventListener("appinstalled", onAppInstalled);

    // على iOS: نُظهر البانر دائماً في display-mode: browser (غير مثبتة).
    if (iOS && window.matchMedia("(display-mode: browser)").matches) {
      setShow(true);
    }

    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
      window.removeEventListener("appinstalled", onAppInstalled);
    };
  }, []);

  if (!show) return null;

  const handleInstall = () => {
    if (deferred) {
      deferred.prompt();
      void deferred.userChoice.then((choice) => {
        if (choice.outcome === "accepted") {
          setShow(false);
        }
      });
    }
  };

  return (
    <div
      className="fixed bottom-4 left-1/2 -translate-x-1/2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm shadow-lg"
      dir="rtl"
    >
      {isIOS ? (
        <div className="flex items-center gap-3">
          <span>📱</span>
          <span>
            اضغط على زر المشاركة، ثم «إضافة إلى الشريحة» لتثبيت الموقع.
          </span>
        </div>
      ) : (
        <button
          onClick={handleInstall}
          disabled={!deferred}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
        >
          تثبيت التطبيق
        </button>
      )}
    </div>
  );
}
