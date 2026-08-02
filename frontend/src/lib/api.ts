/**
 * عميل الـ API — الدردشة عبر SSE (قراءة تدفقية) + نقاط السجل.
 */

import type { ProviderSettings } from "./settings";

export interface ChatEvent {
  type: "conversation" | "delta" | "done" | "error";
  id?: number;
  content?: string;
  detail?: string;
  message_id?: number;
}

export interface Message {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
}

export async function streamChat(
  message: string,
  conversationId: number | null,
  settings: ProviderSettings,
  onEvent: (e: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      provider: settings.provider,
      model: settings.model,
      base_url: settings.provider === "custom" ? settings.baseUrl : undefined,
      api_key: settings.apiKey || undefined,
    }),
    signal,
  });

  if (!res.ok || !res.body) {
    const detail =
      (await res.json().catch(() => null))?.detail ?? `HTTP ${res.status}`;
    throw new Error(detail);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // فصل الأحداث: سطور تبدأ بـ "data: "
    let idx: number;
    while ((idx = buffer.indexOf("\n")) !== -1) {
      const line = buffer.slice(0, idx).trim();
      buffer = buffer.slice(idx + 1);
      if (line.startsWith("data: ")) {
        onEvent(JSON.parse(line.slice(6)) as ChatEvent);
      }
    }
  }
}

export async function fetchHistory(): Promise<Conversation[]> {
  const res = await fetch("/api/chat/history");
  if (!res.ok) throw new Error("فشل تحميل السجل");
  return res.json();
}

export async function fetchConversation(
  id: number,
): Promise<{ conversation: Conversation; messages: Message[] }> {
  const res = await fetch(`/api/chat/${id}`);
  if (!res.ok) throw new Error("فشل تحميل المحادثة");
  return res.json();
}

// ---------- المستندات (م5) ----------
export async function uploadDocument(
  file: File,
): Promise<{ id: number; filename: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/documents", { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text().catch(() => "فشل الرفع"));
  return res.json();
}

export async function fetchDocuments(): Promise<DocumentItem[]> {
  const res = await fetch("/api/documents");
  if (!res.ok) throw new Error("فشل تحميل المستندات");
  return res.json();
}

export interface DocumentItem {
  id: number;
  filename: string;
  file_type: string;
  created_at: string;
}

// ---------- "اسأل كتابك" (م7) ----------
export interface RAGSource {
  document_id: number;
  filename: string;
  heading: string;
  text: string;
  score: number;
}

export interface AskEvent {
  type: "conversation" | "sources" | "delta" | "done" | "error";
  id?: number;
  sources?: RAGSource[];
  content?: string;
  message_id?: number;
  conversation_id?: number;
  detail?: string;
}

export async function streamAsk(
  question: string,
  conversationId: number | null,
  settings: ProviderSettings,
  onEvent: (e: AskEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch("/api/rag/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      conversation_id: conversationId,
      provider: settings.provider,
      model: settings.model,
      base_url: settings.provider === "custom" ? settings.baseUrl : undefined,
      api_key: settings.apiKey || undefined,
    }),
    signal,
  });
  if (!res.ok || !res.body) {
    const detail =
      (await res.json().catch(() => null))?.detail ?? `HTTP ${res.status}`;
    throw new Error(detail);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buffer.indexOf("\n")) !== -1) {
      const line = buffer.slice(0, idx).trim();
      buffer = buffer.slice(idx + 1);
      if (line.startsWith("data: ")) {
        onEvent(JSON.parse(line.slice(6)) as AskEvent);
      }
    }
  }
}

export async function indexDocument(
  id: number,
): Promise<{ document_id: number; indexed: number }> {
  const res = await fetch(`/api/rag/index/${id}`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text().catch(() => "فشل الفهرسة"));
  return res.json();
}

// ---------- البحث على الويب (م8) ----------
export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
}

export async function searchWeb(query: string): Promise<SearchResult[]> {
  const res = await fetch("/api/websearch/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, max_results: 5 }),
  });
  if (!res.ok) throw new Error(await res.text().catch(() => "فشل البحث"));
  return (await res.json()).results;
}

// ---------- الإضافات (م9) ----------
export interface PluginItem {
  name: string;
  version: string;
  type: string;
  title: string;
  description: string;
  status: string;
  failures: number;
  last_error: string;
  permissions: string[];
}

export async function fetchPlugins(): Promise<PluginItem[]> {
  const res = await fetch("/api/plugins");
  if (!res.ok) throw new Error("فشل تحميل الإضافات");
  return res.json();
}

export async function enablePlugin(name: string): Promise<PluginItem> {
  const res = await fetch(`/api/plugins/${name}/enable`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text().catch(() => "فشل التفعيل"));
  return res.json();
}

export async function disablePlugin(name: string): Promise<PluginItem> {
  const res = await fetch(`/api/plugins/${name}/disable`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text().catch(() => "فشل التعطيل"));
  return res.json();
}

export async function invokePlugin(
  name: string,
  args: Record<string, unknown>,
): Promise<unknown> {
  const res = await fetch(`/api/plugins/${name}/invoke`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(args),
  });
  if (!res.ok) throw new Error(await res.text().catch(() => "فشل التنفيذ"));
  return res.json();
}

export async function indexPluginForRag(
  name: string,
): Promise<{ indexed: unknown }> {
  const res = await fetch(`/api/plugins/${name}/index-for-rag`, {
    method: "POST",
  });
  if (!res.ok) {
    const detail =
      (await res.json().catch(() => null))?.detail ?? `HTTP ${res.status}`;
    throw new Error(detail);
  }
  return res.json();
}

// ---------- تقارير AI (م9.3) ----------
export interface ReportSource {
  document_id: number;
  filename: string;
  heading: string;
  text: string;
  score: number;
}

export interface GeneratedReport {
  topic: string;
  markdown: string;
  sources: ReportSource[];
  report_ident: number;
  plugin: string;
}

export async function generatePluginReport(
  name: string,
  topic: string,
): Promise<GeneratedReport> {
  const res = await fetch(`/api/plugins/${name}/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic }),
  });
  if (!res.ok) {
    const detail =
      (await res.json().catch(() => null))?.detail ?? `HTTP ${res.status}`;
    throw new Error(detail);
  }
  return res.json();
}

export async function fetchPluginStorage(
  name: string,
): Promise<{ items: Record<string, string>[] }> {
  const res = await fetch(`/api/plugins/${name}/storage`);
  if (!res.ok) return { items: [] };
  return res.json();
}

export async function savePluginStorage(
  name: string,
  items: Record<string, string>[],
): Promise<{ saved: boolean }> {
  const res = await fetch(`/api/plugins/${name}/storage`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items }),
  });
  if (!res.ok) throw new Error(await res.text().catch(() => "فشل الحفظ"));
  return res.json();
}
