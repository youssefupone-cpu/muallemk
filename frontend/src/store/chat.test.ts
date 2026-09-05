import { beforeEach, describe, expect, it, vi } from "vitest";

import { useChatStore } from "./chat";
import * as api from "../lib/api";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof api>();
  return { ...actual, streamChat: vi.fn() };
});

describe("useChatStore", () => {
  beforeEach(() => {
    useChatStore.setState({
      conversations: [],
      currentId: null,
      messages: [],
      streaming: false,
      error: null,
    });
  });

  it("يدير تدفق الدردشة (start → delta → done)", async () => {
    vi.mocked(api.streamChat).mockImplementation(
      async (_text, _id, _settings, onEvent) => {
        await onEvent({ type: "start" });
        await onEvent({ type: "delta", content: "مرحبا" });
        await onEvent({ type: "delta", content: " بك" });
        await onEvent({ type: "done", content: "مرحبا بك", message_id: 1 });
      },
    );
    const store = useChatStore.getState();
    await store.send("مرحبا", { provider: "ollama", model: "gemma3:1b" });
    const msgs = useChatStore.getState().messages;
    expect(msgs[0].role).toBe("user");
    expect(useChatStore.getState().streaming).toBe(false);
    expect(msgs.length).toBe(2);
    expect(msgs[1].role).toBe("assistant");
    expect(msgs[1].content).toBe("مرحبا بك");
  });

  it("يدوّن الخطأ عند فشل الاتصال", async () => {
    vi.mocked(api.streamChat).mockRejectedValue(new Error("خادم غير متاح"));
    const store = useChatStore.getState();
    await store.send("سؤال", { provider: "ollama", model: "gemma3:1b" });
    expect(useChatStore.getState().error).toContain("خادم غير متاح");
    expect(useChatStore.getState().streaming).toBe(false);
  });
});
