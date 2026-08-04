import { describe, expect, it } from "vitest";

import { readSSE } from "./api";

/** محاكاة Response بسيطة لتجربة readSSE (P4-202) */
function mockResponse(lines: string[]): Response {
  const text = lines.join("\n");
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(text));
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

describe("readSSE", () => {
  it("يدقق الـ JSON من أحداث data: ", async () => {
    const res = mockResponse([
      'data: {"type":"start"}',
      'data: {"type":"delta","content":"ه"}',
      'data: {"type":"done"}',
      "",
    ]);
    const events: unknown[] = [];
    await readSSE(res, (e) => events.push(e));
    expect(events).toHaveLength(3);
    expect((events[0] as { type: string }).type).toBe("start");
    expect((events[2] as { type: string }).type).toBe("done");
  });

  it("يرمي خطأ عند استجابة فاشلة", async () => {
    const res = new Response(JSON.stringify({ detail: "غير مخول" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
    await expect(readSSE(res, () => {})).rejects.toThrow("غير مخول");
  });
});
