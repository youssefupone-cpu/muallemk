import { describe, expect, it } from "vitest";

import { errMsg, isAbortError } from "./utils";

describe("errMsg", () => {
  it("يستخرج الرسالة من Error", () => {
    expect(errMsg(new Error("فشل الاتصال"))).toBe("فشل الاتصال");
  });

  it("يعيد string كما هو", () => {
    expect(errMsg("خطأ يدوي")).toBe("خطأ يدوي");
  });

  it("يعالج unknown object مع message", () => {
    const err = { message: "خطأ غير معياري" };
    expect(errMsg(err)).toBe("خطأ غير معياري");
  });

  it("يعيد رسالة افتراضية للقيم غير المعروفة", () => {
    expect(errMsg(null)).toBe("تعذّر الاتصال بالخادم");
    expect(errMsg(undefined)).toBe("تعذّر الاتصال بالخادم");
    expect(errMsg(42)).toBe("تعذّر الاتصال بالخادم");
    expect(errMsg({})).toBe("تعذّر الاتصال بالخادم");
  });
});

describe("isAbortError", () => {
  it("يتعرف على AbortError من Error", () => {
    const e = new Error("إلغاء العملية");
    e.name = "AbortError";
    expect(isAbortError(e)).toBe(true);
  });

  it("يتعرف على AbortError من plain object", () => {
    expect(isAbortError({ name: "AbortError", message: "aborted" })).toBe(true);
  });

  it("يعيد false للأخطاء العادية", () => {
    expect(isAbortError(new Error("خطأ آخر"))).toBe(false);
    expect(isAbortError("نص عادي")).toBe(false);
    expect(isAbortError(null)).toBe(false);
    expect(isAbortError({ name: "TypeError" })).toBe(false);
  });
});
