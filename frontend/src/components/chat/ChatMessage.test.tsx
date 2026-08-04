import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChatMessage } from "./ChatMessage";
import type { Message } from "../../lib/api";

const baseMessage: Message = {
  id: 1,
  role: "assistant",
  content: "",
  created_at: "2026-08-04T00:00:00Z",
};

describe("ChatMessage", () => {
  it("يدخِّر المعادلات النصية الداخلية إلى KaTeX", () => {
    const { container } = render(
      <ChatMessage
        message={{
          ...baseMessage,
          role: "assistant",
          content: "المعادلة: $E = mc^2$",
        }}
      />,
    );
    // rehype-katex يحوِّل $...$ إلى .katex
    expect(container.querySelector(".katex")).not.toBeNull();
    expect(container.querySelector(".katex span")).not.toBeNull();
  });

  it("يمنع XSS — يزيل <script> وonerror وروابط javascript:", () => {
    const { container } = render(
      <ChatMessage
        message={{
          ...baseMessage,
          role: "assistant",
          content:
            '<script>alert(1)</script><img src="x" onerror="alert(2)" /><a href="javascript:alert(3)">رابط</a>',
        }}
      />,
    );
    // rehype-sanitize يزيل العنصر <script> تماماً
    expect(container.querySelector("script")).toBeNull();
    // لا أي نافذة onerror طفوية في الشجرة
    expect(container.querySelector("[onerror]")).toBeNull();
    // لا رابط javascript:
    expect(container.querySelector('a[href^="javascript:"]')).toBeNull();
  });
});
