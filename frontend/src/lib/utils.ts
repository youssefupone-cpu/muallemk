import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * استخراج رسالة خطأ آمنة — تعمل مع Error، string، أو unknown.
 * تحل مشكلة `(err as Error).message` الذي يعيد `undefined` للـ non-Error throws.
 */
export function errMsg(err: unknown): string {
  if (err instanceof Error) return err.message;
  if (typeof err === "string") return err;
  if (err && typeof err === "object" && "message" in err) {
    return String((err as Record<string, unknown>).message);
  }
  return "تعذّر الاتصال بالخادم";
}

/** هل الخطأ ناتج عن إلغاء المستخدم (AbortController/AbortSignal)؟ */
export function isAbortError(err: unknown): boolean {
  if (err instanceof Error) return err.name === "AbortError";
  if (err && typeof err === "object" && "name" in err) {
    return (err as Record<string, unknown>).name === "AbortError";
  }
  return false;
}
