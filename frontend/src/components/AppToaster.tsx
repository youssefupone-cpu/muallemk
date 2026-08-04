import { Toaster } from "./ui/sonner";

/**
 * شريط إشعارات موحد (P4-246/169) — يحل محل Toast المهجور.
 * يُستورد في AppLayout أو الجذر. يدعم dark mode تلقائياً.
 */
export function AppToaster() {
  return (
    <Toaster
      richColors
      closeButton
      position="top-left"
      toastOptions={{
        className:
          "bg-white dark:bg-slate-900 dark:text-slate-50 dark:border-slate-700",
        duration: 4000,
      }}
    />
  );
}
