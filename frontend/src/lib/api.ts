/**
 * عميل الـ API — الدردشة عبر SSE (قراءة تدفقية) + نقاط السجل.
 */

import type { ProviderSettings } from "./settings";

export interface ChatEvent {
  type: "start" | "conversation" | "delta" | "done" | "error";
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

/**
 * قارئ SSE العام — يقرأ البث ويدعّ callback لكل خط `data: `.
 * يرمي Error مع رسالة detail عند الاستجابات الخطأ (P4-202).
 */
export async function readSSE(
  res: Response,
  onEvent: (e: unknown) => void,
  signal?: AbortSignal,
): Promise<void> {
  if (!res.ok) {
    const detail =
      (await res.json().catch(() => null))?.detail ?? `HTTP ${res.status}`;
    throw new Error(detail);
  }
  if (!res.body) return;

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buffer.indexOf("\n")) !== -1) {
      const line = buffer.slice(0, idx).trim();
      buffer = buffer.slice(idx + 1);
      if (line.startsWith("data: ")) {
        try {
          onEvent(JSON.parse(line.slice(6)));
        } catch (e) {
          if (import.meta?.env?.DEV) console.warn("Malformed SSE line:", line, e);
        }
      }
    }
  }
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
    headers: { "Content-Type": "application/json", "x-provider-key": settings.apiKey || "" },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      provider: settings.provider,
      model: settings.model,
      base_url: settings.provider === "custom" ? settings.baseUrl : undefined,
    }),
    signal,
  });

  if (!res.ok || !res.body) {
    const detail =
      (await res.json().catch(() => null))?.detail ?? `HTTP ${res.status}`;
    throw new Error(detail);
  }

  await readSSE(res, (e) => onEvent(e as ChatEvent), signal);
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
    headers: { "Content-Type": "application/json", "x-provider-key": settings.apiKey || "" },
    body: JSON.stringify({
      question,
      conversation_id: conversationId,
      provider: settings.provider,
      model: settings.model,
      base_url: settings.provider === "custom" ? settings.baseUrl : undefined,
    }),
    signal,
  });
  if (!res.ok || !res.body) {
    const detail =
      (await res.json().catch(() => null))?.detail ?? `HTTP ${res.status}`;
    throw new Error(detail);
  }

  await readSSE(res, (e) => onEvent(e as AskEvent), signal);
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

// ---------- الكتب (P2) ----------

export interface BookItem {
  id: number;
  filename: string;
  title: string;
  file_type: string;
  status: string;
  unit_count: number;
  lesson_count: number;
  created_at: string;
  updated_at: string;
}

export interface BookLesson {
  id: number;
  book_id: number;
  unit_index: number;
  unit_title: string;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface BookDetail {
  book: BookItem;
  units: Array<{
    index: number;
    title: string;
    lessons: BookLesson[];
  }>;
}

export interface LessonContent {
  id: number;
  book_id: number;
  unit_index: number;
  unit_title: string;
  title: string;
  status: string;
  content: string;
  questions: Array<{
    question: string;
    answer: string;
    type?: string;
    options?: string[];
    explanation?: string;
  }>;
  exercises: Array<{ question: string; hint?: string; answer?: string }>;
  glossary: Array<{ term: string; definition: string }>;
  created_at: string;
  updated_at: string;
}

export interface QuizBankItem {
  id: number;
  book_id: number;
  lesson_id: number;
  question: string;
  qtype: string;
  options: string;
  answer: string;
}

export interface GenerateResult {
  generated: number[];
  failed: Array<{ lesson_id: number; error: string }>;
}

export async function fetchBooks(): Promise<BookItem[]> {
  const res = await fetch("/api/books");
  if (!res.ok) throw new Error("فشل تحميل الكتب");
  return res.json();
}

export async function fetchBook(id: number): Promise<BookDetail> {
  const res = await fetch(`/api/books/${id}`);
  if (!res.ok) throw new Error("فشل تحميل الكتاب");
  return res.json();
}

export async function uploadBook(file: File): Promise<BookItem> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/books/upload", { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text().catch(() => "فشل رفع الكتاب"));
  return res.json();
}

export async function deleteBook(id: number): Promise<void> {
  const res = await fetch(`/api/books/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await res.text().catch(() => "فشل حذف الكتاب"));
}

export async function analyzeBook(id: number): Promise<BookLesson[]> {
  const res = await fetch(`/api/books/${id}/analyze`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text().catch(() => "فشل تحليل الكتاب"));
  return res.json();
}

export async function generateBookLessons(
  id: number,
  lessonIds: number[] | null,
  settings: ProviderSettings,
): Promise<GenerateResult> {
  const res = await fetch(`/api/books/${id}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-provider-key": settings.apiKey || "" },
    body: JSON.stringify({
      lesson_ids: lessonIds,
      provider: settings.provider,
      model: settings.model,
      base_url: settings.provider === "custom" ? settings.baseUrl : undefined,
    }),
  });
  if (!res.ok) throw new Error(await res.text().catch(() => "فشل توليد الدروس"));
  return res.json();
}

export async function fetchLesson(id: number): Promise<LessonContent> {
  const res = await fetch(`/api/books/lessons/${id}`);
  if (!res.ok) throw new Error("فشل تحميل الدرس");
  return res.json();
}

export async function regenerateLesson(
  lessonId: number,
  settings: ProviderSettings,
): Promise<GenerateResult> {
  const res = await fetch(`/api/books/lessons/${lessonId}/regenerate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-provider-key": settings.apiKey || "" },
    body: JSON.stringify({
      provider: settings.provider,
      model: settings.model,
      base_url: settings.provider === "custom" ? settings.baseUrl : undefined,
    }),
  });
  if (!res.ok) throw new Error(await res.text().catch(() => "فشل إعادة التوليد"));
  return res.json();
}

export async function searchLessons(
  q: string,
): Promise<Array<{ id: number; book_id: number; title: string; unit_title: string; snippet: string }>> {
  const res = await fetch(`/api/books/search?q=${encodeURIComponent(q)}`);
  if (!res.ok) throw new Error("فشل البحث");
  return res.json();
}

export async function exportQuizJson(
  bookId: number,
): Promise<{ count: number; items: QuizBankItem[] }> {
  const res = await fetch(`/api/books/quiz/export?book_id=${bookId}`);
  if (!res.ok) throw new Error("فشل تصدير الأسئلة");
  return res.json();
}

export async function importQuizJson(
  bookId: number,
  items: Record<string, unknown>[],
): Promise<{ imported: number }> {
  const res = await fetch("/api/books/quiz/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ book_id: bookId, items }),
  });
  if (!res.ok) throw new Error(await res.text().catch(() => "فشل استيراد الأسئلة"));
  return res.json();
}

export async function fetchQuiz(bookId: number): Promise<QuizBankItem[]> {
  const res = await fetch(`/api/books/${bookId}/quiz`);
  if (!res.ok) throw new Error("فشل تحميل الأسئلة");
  return res.json();
}

export async function submitQuizAttempt(
  quizId: number,
  answer: string,
): Promise<{ is_correct: boolean }> {
  const res = await fetch(`/api/books/quiz/${quizId}/attempt`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer }),
  });
  if (!res.ok) throw new Error("فشل تسجيل المحاولة");
  return res.json();
}
