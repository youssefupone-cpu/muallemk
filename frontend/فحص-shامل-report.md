# Frontend Audit Report — معلّمك (React 19 + Vite + Tailwind v4)

**Project:** `/home/youssef-ayad/Desktop/projects/project3/frontend`
**Date:** 2026-08-04
**Stack:** React 19.2.8, Vite 8.2, Tailwind v4.3, Zustand 5.0, React Query 5.1, Recharts 3.10, react-markdown 10.1, React Compiler (babel), oxlint, vitest, playwright

---

## 1. Verification Results

| Check | Command | Result |
|-------|---------|--------|
| Type-check (app) | `npx tsc --noEmit -p tsconfig.app.json` | ✅ Clean (0 errors) |
| Type-check (project refs) | `npx tsc -b --noEmit` | ✅ Clean (0 errors) |
| Build | `npx vite build` | ✅ Built in 6.07s |
| Unit tests | `npx vitest run` | ✅ 5 files, 9 tests, all pass |
| Lint | `npx oxlint` | ⚠️ 1 warning |

### Build output notes
- Main JS chunk: **856.90 kB** (261.13 kB gzipped) — large
- 28 KaTeX font assets emitted (~200 kB total)
- 6 PWA precache entries (907.73 KiB)
- Plugin timing warning: `@rolldown/plugin-babel` 52% of build time

### ESLint/oxlint warning
```
src/components/ThemeProvider.tsx:54:14: warning react(only-export-components)
  useTheme exported alongside ThemeProvider component — break it into its own file.
```

---

## 2. Architecture & Structure

### Tech Stack Summary
- **Bundler/Vite:** Vite 8.2 with `@vitejs/plugin-react` v6 + `@rolldown/plugin-babel` for React Compiler (non-standard setup)
- **Build pipeline:** `react()` → `babel({ presets: [reactCompilerPreset()] })` — workaround for v6 removing the `babel` option
- **State:** Zustand 5 for chat state (local, in-memory); React Query 5 for history/documents
- **Routing:** React Router DOM 7 — 8 routes (7 pages + 404)
- **Styling:** Tailwind v4 with `@tailwindcss/vite` plugin; custom `@custom-variant dark` syntax
- **Internationalization:** RTL via `dir="rtl"` in `index.html` + `index.css`; Arabic (ar-EG) locale strings throughout
- **PWA:** `vite-plugin-pwa` 1.3; Workbox runtime caching for `/api/books` (NetworkFirst) and `/api/rag/ask` (NetworkOnly)
- **Math:** `react-katex` + `remark-math`/`rehype-katex`; `react-markdown` v10 with `rehype-sanitize` for XSS safety

### Route Map
| Route | Component | Layout |
|-------|-----------|--------|
| `/` | `ChatPage` | **Custom** (no AppLayout) |
| `/settings` | `SettingsPage` → `SettingsPanel` | AppLayout |
| `/documents` | `DocumentsPage` | AppLayout |
| `/books` | `BooksPage` | AppLayout |
| `/exam` | `ExamPage` | AppLayout |
| `/diagnostic` | `DiagnosticPage` | AppLayout |
| `/plugins` | `PluginsPage` | AppLayout |
| `/plugins/study-table` | `StudyTablePage` | AppLayout |
| `*` | `NotFoundPage` | AppLayout |

**Key inconsistency:** `ChatPage` is the only page that does NOT use `AppLayout`. It has its own inline header/nav/conversation-list layout. This means:
- Inconsistent navigation styling across the app
- No shared header with the rest of the app
- The conversation sidebar (`ConversationList`, fixed `w-64`) doesn't collapse on mobile

### Component Inventory
| File | Purpose |
|------|---------|
| `App.tsx` | Root — routes + `<ReloadPrompt>` |
| `main.tsx` | React 19 root render with StrictMode, BrowserRouter, QueryClientProvider, ErrorBoundary, ThemeProvider |
| `ThemeProvider` / `theme-helmet.js` | Zero-FOUC theme with inline pre-bootstrap script |
| `ChatMessage` | Markdown + KaTeX + XSS-sanitized message renderer |
| `MathRenderer` | Standalone math/Markdown renderer (duplicates ChatMessage logic) |
| `ChatInput` | Textarea with char count, limit, Send/Loading button |
| `ConversationList` | Sidebar with conversation list, export/delete actions |
| `DragDropUpload` | react-dropzone zone with size/type validation |
| `StudyChart` | Recharts bar chart (**orphaned — never imported**) |
| `ErrorBoundary` | Class component fallback with retry button |
| `AppToaster` | sonner Toaster wrapper (rendered inside ReloadPrompt) |
| `ReloadPrompt` | PWA update notification + service worker registration |
| `SettingsPanel` | Provider/model/temperature config form (localStorage-backed) |

### Data Flow
1. `ChatPage` calls `useChatStore.send()` → stores call `streamChat()` → SSE via `readSSE()` in `lib/api.ts:174`
2. React Query fetches history on `ChatPage` load → populates Zustand `conversations`
3. `DocumentsPage` uses React Query for documents; SSE for RAG questions (`streamAsk`)
4. `BooksPage` uses manual `useState` + `useEffect` (not React Query) for books/lessons
5. Settings read from `localStorage` directly in components (not reactive)

---

## 3. TypeScript Issues (`any`, `unknown`, type-safety)

### Severity distribution: 3 Critical, 5 High, 8 Medium

#### Critical

1. **`api_key` sent in POST request body** (`api.ts:42, 162, 509, 637`)
   ```ts
   // api.ts:42
   body: JSON.stringify({
     ...
     api_key: settings.apiKey || undefined,
   })
   ```
   API keys travel in the request body, visible in browser Network tab, server access logs, and proxy logs. Should use HTTPS-only headers and never log request bodies. The comment says "يُرسل مرة واحدة مع طلب التوليد" but POST bodies are still logged by many proxy/middleware setups.

2. **27 instances of `(err as Error)` across 5 files** (no runtime guard)
   Every `catch` block casts to `Error` without checking `instanceof Error`:
   ```ts
   // 13 instances in BooksPage.tsx alone
   catch (err) { setError((err as Error).message); }
   ```
   If the catch receives a non-Error (string, undefined, object), `(err as Error).message` is `undefined`, producing no error text. Should use a helper: `function errMsg(e: unknown): string { return e instanceof Error ? e.message : String(e); }`

3. **`unknown` return types leak into component-level type assertions** (`BooksPage.tsx:620,635`)
   ```ts
   q={q as unknown as Record<string, unknown>}
   e={e as unknown as Record<string, unknown>}
   ```
   `BookQuestion` is a well-defined interface in `api.ts:386` but `LessonContent.questions` returns `BookQuestion[]`. The `QuestionRenderer`/`ExerciseRenderer` components accept `Record<string, unknown>` instead of the proper types — this defeats TypeScript entirely. Should accept `BookQuestion` directly.

#### High

4. **Duplicate KaTeX CSS imports** — 3 locations
   ```ts
   // index.css:2
   @import "katex/dist/katex.min.css";
   // api.ts/MathRenderer.tsx:4
   import "katex/dist/katex.min.css";
   // ChatMessage.tsx:7
   import "katex/dist/katex.min.css";
   ```
   Vite deduplicates at build time, but this is redundant and confusing. Remove the two component-level imports.

5. **`invokePlugin` returns `Promise<unknown>`** (`api.ts:268`)
   Caller in `PluginsPage.tsx:70` immediately casts: `as { result: {...} }`. This bypasses type safety at both ends. Should define a proper return type per plugin.

6. **`indexPluginForRag` returns `{ indexed: unknown }`** (`api.ts:280`)
   Caller in `PluginsPage.tsx:204` checks `r.indexed && Array.isArray(r.indexed)` — the `unknown` type forces runtime checks that TypeScript should guarantee. Should be `{ indexed: number }` or a discriminated union.

7. **`exportQuizJson` returns `items: unknown[]`** (`api.ts:603`)
   The import flow in `BooksPage.tsx:332` does `JSON.parse` then passes `unknown[]` to `importQuizJson(bookId, items)` — no type safety on the shape of quiz items.

8. **No abort controller for chat streaming** (`store/chat.ts:123`)
   `streamChat` accepts an `AbortSignal` parameter but the store's `send` method never passes one:
   ```ts
   // chat.ts:123
   await streamChat(text, get().currentId, settings, onEvent);
   // signal parameter is never passed!
   ```
   Unlike `DocumentsPage` (which correctly creates `AbortController`), the main chat flow has no way to cancel an in-flight request. The `streamChat` API signature includes `signal?: AbortSignal` but it's dead code for the chat store.

#### Medium

9. **`ChatInput.tsx:35`** — `e as unknown as FormEvent`
   ```ts
   onKeyDown={(e) => {
     if (e.key === "Enter" && !e.shiftKey) {
       e.preventDefault();
       submit(e as unknown as FormEvent); // KeyboardEvent → FormEvent cast
     }
   }}
   ```
   The `submit` function only uses `e.preventDefault()`, which both `KeyboardEvent` and `FormEvent` have. Should refactor to accept `preventDefault` capability or just call `e.preventDefault()` directly here and pass the text.

10. **No explicit return types on components** — all 16 component/page functions lack explicit return type annotations (`App`, `ChatPage`, `DocumentsPage`, etc.). `tsconfig` has `strict: true` but doesn't enforce return types.

11. **`PluginUiItem` double-extends with runtime cast** (`StudyTablePage.tsx:17-25`)
    ```ts
    interface PluginUiItem extends PluginItem {
      ui?: { schema?: { items?: { properties?: Record<string, {...}> } }; };
    }
    ```
    Then accessed via `(p as PluginUiItem).ui?.schema?.items?.properties` — a runtime shape assumption on an `unknown`-ish `PluginItem` field. The API `PluginItem` type doesn't include `ui` — this is entirely undocumented data. Should be part of the API type or validated at runtime.

12. **`loadSettings()` called synchronously in render-time** (`DocumentsPage.tsx:27`, `BooksPage.tsx:206`, `ChatPage.tsx:152`)
    Settings are read from `localStorage` on component render via `loadSettings()`, not inside `useEffect`. While this works (localStorage is synchronous), it's not reactive — if the user changes settings in another tab, this component won't update.

13. **`tsconfig.app.json` has `erasableSyntaxOnly: true`** — this prevents certain TS features but is correct for this project. No issue.

14. **`vite-env.d.ts`** declares a virtual module type but `vite.config.ts` doesn't register it — the PWA plugin from `vite-plugin-pwa` provides this. Works in practice but the relationship is implicit.

---

## 4. Performance Issues

### Severity: 1 Critical, 3 High, 4 Medium

#### Critical

1. **Bundle size: 856.90 kB JS (261.13 kB gzipped)** for a frontend-only app
   - Primary contributors: `react-katex` + 28 KaTeX font files (~200 kB), `recharts` (~300+ kB), `react-markdown` + plugins, `lucide-react` (all icons imported by default)
   - **No code splitting** — entire app is one chunk. Vite default config uses manual chunking only for async chunks. All routes are eagerly imported in `App.tsx`.
   - **Fix:** Configure `build.rollupOptions.output.manualChunks` or use `React.lazy` + `Suspense` for route-level splitting.

2. **`lucide-react` fully imported** — `ChatMessage.tsx`, `ChatInput.tsx`, `ConversationList.tsx`, `DragDropUpload.tsx`, `PluginsPage.tsx`, etc. all import specific icons (`Bot`, `User`, `SendHorizonal`, etc.), which is correct. But the full icon set is still bundled if any barrel imports exist. *Actually OK* — individual imports are used.

#### High

3. **React Compiler setup is non-standard and time-consuming**
   ```ts
   // vite.config.ts:13-14
   react(),
   babel({ presets: [reactCompilerPreset()] }),
   ```
   Comment says: v6 removed the `babel` option from `react()`, so they use `@rolldown/plugin-babel` as a workaround. This adds 52% of build time. The `@rolldown/plugin-babel` + `babel-plugin-react-compiler` is correct for Vite 8 / Rolldown.

4. **`@apply` / Tailwind JIT generate at build time** — `@tailwindcss/vite:generate:build` takes 7% of build time. No issue but worth noting.

5. **ChatPage scroll on every message** — `useEffect` triggers `scrollIntoView` on every `messages` change, including during streaming (each delta update). This can cause jank on slow devices.
   ```ts
   // ChatPage.tsx:78-80
   useEffect(() => {
     bottomRef.current?.scrollIntoView({ behavior: "smooth" });
   }, [messages]);
   ```
   **Fix:** Throttle/debounce or check if user is near the bottom before auto-scrolling.

#### Medium

6. **Duplicate KaTeX CSS imports** (see TypeScript section) — at runtime, CSS `@import` + ES `import` might cause double-fetch on first load.

7. **`MathRenderer.tsx`** duplicates logic from `ChatMessage.tsx` — both import the same markdown/katex stack. If `MathRenderer` is used elsewhere, they should share a common render config.

8. **No `React.memo` on any component** — `ChatMessage`, `ConversationList`, `ChatInput` all re-render on every store change even if their props don't change. `ChatMessage` especially (re-renders on each delta during streaming for the entire message list, not just the active message).

9. **`BooksPage.tsx`** has 4 inline sub-components (`Flashcards`, `LessonView`, `QuestionRenderer`, `ExerciseRenderer`) — none are memoized, causing re-renders when the parent's state changes.

---

## 5. Accessibility Issues

### Severity: 1 Critical, 4 High, 6 Medium, 2 Low

#### Critical

1. **No `aria-live` region for streaming content** (`ChatMessage.tsx`, `DocumentsPage.tsx:183`)
   When the assistant streams a response, screen reader users get no announcement. The message container needs `aria-live="polite"` or `aria-relevant="additions text"`. Currently:
   ```tsx
   // ChatMessage.tsx:25-30 — no aria-live, no role
   <div className={cn("max-w-[80%] rounded-2xl ...")}>
   ```
   **Fix:** Add `aria-live="polite"` to the messages container in `ChatPage`.

#### High

2. **Avatar icons have no accessible labels** (`ChatMessage.tsx:21,84`)
   ```tsx
   // User avatar
   <div className="flex size-8 ..."><User className="size-4 text-slate-600" /></div>
   // Bot avatar
   <div className="flex size-8 ..."><Bot className="size-4 text-white" /></div>
   ```
   `User` and `Bot` are decorative icons with no `aria-hidden` or `role="img"` + `aria-label`. Screen readers will announce nothing.
   **Fix:** Add `aria-hidden="true"` to decorative icons.

3. **`ChatInput` textarea has no `aria-label`** (`ChatInput.tsx:29-46`)
   The placeholder says "اكتب سؤالك الدراسي…" but placeholders disappear on input and aren't read by all screen readers. The send button has no `aria-label` (just an icon).
   **Fix:** Add `aria-label="اكتب سؤالك الدراسي"` to textarea; `aria-label="إرسال"` to button.

4. **MCQ answer buttons have no semantic role/label** (`ExamPage.tsx:219`, `DiagnosticPage.tsx:156`)
   ```tsx
   <button onClick={() => void answer(opt)}>{opt}</button>
   ```
   These are answer options but don't convey that they're radio choices. Should use `role="radio"` or be in a `role="radiogroup"` with `aria-checked`.

5. **No skip links on any page** — keyboard users must tab through the entire navigation to reach main content. `AppLayout` has `<main>` but no skip link.

#### Medium

6. **`ErrorBoundary` retry button has no `aria-label`** (`ErrorBoundary.tsx:36-40`)
   ```tsx
   <button onClick={...} className="...">إعادة المحاولة</button>
   ```
   Has visible text "إعادة المحاولة" so this is actually OK. *Not a real issue.*

7. **Timer in ExamPage has no time-remaining announcement** (`ExamPage.tsx:198-207`)
   The timer changes color at `< 120s` but screen readers get no audio cue. Need `aria-live` for time warnings.

8. **`DragDropUpload` uses `toast()` for progress** (`DragDropUpload.tsx:47`)
   Progress updates via `sonner` toast are visual-only. Screen readers get no announcement. The progress toast `id="upload-progress"` is reused but `toast()` doesn't set `aria-live`.

9. **`Flashcards` component** (`BooksPage.tsx:55-91`) uses `role="button"` + `aria-label="اقلِب البطاقة"` — **correct implementation**. Good.

10. **Table in `StudyTablePage` has no `<caption>` or `aria-label`** (`StudyTablePage.tsx:156`)
    Screen readers can't understand the table's purpose.

11. **Form inputs in `SettingsPanel` use `<label>` wrapping** — **correct**. Good.

12. **`StudyTablePage` delete button** has visible text "حذف" so it's accessible.

#### Low

13. **`ThemeToggle` has `aria-label`** — ✅ correct (`ThemeToggle.tsx:16`)

14. **`ConversationList` "new conversation" button** (`ConversationList.tsx:33`)
    Has `<MessageSquarePlus className="size-4" />` with `title="محادثة جديدة"` — `title` provides a tooltip but is NOT accessible to screen readers. Should add `aria-label`.

---

## 6. Responsive Design Issues

### Severity: 1 High, 3 Medium

#### High

1. **`ConversationList` has fixed `w-64` sidebar** (`ConversationList.tsx:26`)
   On mobile (screen < 640px), 64 width = 256px, which eats half the screen. The chat layout in `ChatPage` uses this side-by-side:
   ```tsx
   <div className="flex h-screen overflow-hidden">
     <ConversationList />  // always visible, w-64
     <main>...</main>
   </div>
   ```
   On mobile, the conversation list should collapse into a hamburger/drawer. Currently it permanently takes 40% of the viewport.

#### Medium

2. **`BooksPage` lesson content** (`BooksPage.tsx:593`) uses `whitespace-pre-wrap` for lesson text but no responsive typography. Long lines on mobile cause excessive horizontal scrolling.

3. **`StudyTablePage` table** (`StudyTablePage.tsx:155`) uses `overflow-hidden` instead of `overflow-x-auto` — on small screens, columns are clipped rather than scrollable. Should be:
   ```tsx
   <div className="overflow-x-auto rounded-xl ...">
     <table className="w-full ...">
   ```

4. **`ChatMessage` max-width** (`ChatMessage.tsx:27`)
   ```tsx
   "max-w-[80%]"
   ```
   On very small screens, 80% of viewport might be fine, but the avatar (size-8) + gap-3 + 80% width could overflow. Should use `max-w-[calc(100%-theme(spacing.12))]` for the message bubble on mobile.

---

## 7. RTL (Right-to-Left) Issues

### Severity: 1 High, 2 Medium, 1 Low

#### High

1. **ChatMessage alignment is reversed for RTL convention** (`ChatMessage.tsx:19`)
   ```tsx
   <div className={cn("flex gap-3", isUser ? "justify-start" : "justify-end")}>
   ```
   In RTL (`dir="rtl"`):
   - `justify-start` = LEFT side
   - `justify-end` = RIGHT side

   So user messages appear on the LEFT and assistant on the RIGHT. This is **reversed from standard Arabic chat UI convention** (WhatsApp, Telegram, etc.) where the user's messages are on the RIGHT and the assistant/bot on the LEFT.
   **Fix:** Swap to `isUser ? "justify-end" : "justify-start"`.

   Additionally, the avatar placement follows the alignment — user avatar stays on the left side of the user's message bubble, which is fine for the current (but arguably wrong) layout.

#### Medium

2. **`ChatInput` send button position** (`ChatInput.tsx:27-72`)
   ```tsx
   <div className="flex ... items-end gap-2">
     <div className="flex-1">textarea</div>
     <button>SendHorizonal</button>
   </div>
   ```
   In RTL, flex items flow right-to-left. So the textarea appears on the RIGHT and the send button on the LEFT. This is actually correct for RTL — the send button on the left is the standard position. However, `SendHorizonal` icon points right (→), which in RTL should point left (←). **Fix:** Use `rotate-180` on the icon or use `SendVertical`.

3. **`ChatInput` RTL char count** (`ChatInput.tsx:47-58`)
   ```tsx
   <div className="mt-1 text-left text-[11px] text-slate-400" dir="rtl">
   ```
   Uses `text-left` with explicit `dir="rtl"` — this is redundant and could be confusing. The `dir="rtl"` on the inner div makes `text-left` point to the visual right. Should use `text-right` without the redundant `dir` attribute.

#### Low

4. **`index.css` `direction: rtl`** is set globally on `html` — correct. But `AppLayout.tsx` doesn't set `dir="rtl"` on individual components. Some components use `dir="ltr"` for inputs (`SettingsPanel.tsx:81`) and math (`ChatMessage.tsx:40,42`) — correct usage.

---

## 8. Loading / Error State Issues

### Severity: 1 Critical, 2 High, 4 Medium

#### Critical

1. **`DocumentsPage` shows "no documents" instead of loading** (`DocumentsPage.tsx:126`)
   ```tsx
   {docs.length === 0 && <p>لا مستندات بعد — ارفع كتاباً أو مذكرة.</p>}
   ```
   When `useQuery` is fetching, `docs` defaults to `[]` (from `const { data: docs = [] }`). So the user sees "no documents yet" during loading instead of a spinner. **Fix:** Use `isPending` / `isFetching` state.

#### High

2. **No loading states on `fetchBooks()` in 3 pages**
   `BooksPage.tsx:216`, `ExamPage.tsx:54`, `DiagnosticPage.tsx:42` all call `fetchBooks()` in `useEffect` with no loading state:
   ```tsx
   useEffect(() => { void loadBooks(); }, []);
   // If fetchBooks takes 2s, the book select shows empty with no feedback
   ```
   **Fix:** Add `loading` boolean state and show a skeleton/spinner.

3. **`StudyTablePage` swallows errors during initialization** (`StudyTablePage.tsx:35-58`)
   If `fetchPlugins()` fails, the entire form disappears (no `plugin` → no fields → empty page). No retry is offered.

#### Medium

4. **`BooksPage` uses string for `busy` state** (`BooksPage.tsx:200`)
   ```tsx
   const [busy, setBusy] = useState("");  // "" | "upload" | "analyze"
   ```
   This is a loosely-typed string union instead of a proper enum. If you typo `"uplaod"`, TypeScript won't catch it. Should be `useState<"" | "upload" | "analyze">("")`.

5. **`ExamPage` timer doesn't handle the "done" phase transition cleanly**
   When `secondsLeft <= 1`, `finishExam()` is called inside the `setSecondsLeft` updater. This is a side-effect-in-reducer anti-pattern. The timer also calls `finishExam()` which sets `phase` to `"done"`, but the interval cleanup function (which runs on `phase` change) clears the interval AFTER `finishExam` runs — so there could be a brief moment where the interval fires multiple times near 0.

6. **`ExamPage` allows "show result" before all questions are answered** (`ExamPage.tsx:280-287`)
   ```tsx
   {current >= qa.length && (
     <button onClick={() => finishExam()}>اعرض النتيجة</button>
   )}
   ```
   This button only shows when `current >= qa.length`, but `current` only increments after answering. So the user must answer all questions to see results. But the timer can run out, calling `finishExam()` automatically — there's no "show results now" option for the timer-expired case. This is a minor UX gap.

7. **`BooksPage` onImportQuiz has no loading/error granularity** (`BooksPage.tsx:325-341`)
   If `JSON.parse` fails (malformed file), the error message is "Unexpected token" — not user-friendly. Should show "ملف JSON غير صالح".

8. **`PluginsPage` report generation has nested inline arrow** (`PluginsPage.tsx:230`)
   The report `<button>` has an inline `(e) => { ... }` async arrow that doesn't handle errors well. The `try/catch` is inside but doesn't clear the `result` state on error.

---

## 9. SSE Streaming Analysis

### Severity: 1 Critical, 2 High, 2 Medium

#### Critical

1. **`readSSE` does NOT handle JSON parse errors** (`api.ts:174-199`)
   ```ts
   // api.ts:194-196
   if (line.startsWith("data: ")) {
     onEvent(JSON.parse(line.slice(6)));  // throws if malformed
   }
   ```
   If the server sends malformed JSON (e.g., `data: {broken}`), `JSON.parse` throws synchronously, breaking the stream reader. The caller (`streamChat`) would catch it via `readSSE`'s outer try/catch, but the stream is unrecoverable — the user loses the entire response. **Fix:** Wrap `JSON.parse` in try/catch and emit an error event.

   ```ts
   if (line.startsWith("data: ")) {
     try {
       onEvent(JSON.parse(line.slice(6)));
     } catch {
       onEvent({ type: "error", detail: "استقبت خطأ في بيانات الخادم" });
     }
   }
   ```

2. **`readSSE` does NOT handle SSE comments or `event:`/`id:` lines**
   The SSE spec allows:
   - Comments (lines starting with `:`) — should be ignored
   - `event: <name>` — sets the event type
   - `id: <id>` — sets the event ID
   
   The current parser only handles `data: ` lines. If the server sends comments or uses `event:` prefixes, they'll be ignored (which is OK), but the `JSON.parse` will run on non-data lines that start with `data: `. This is actually fine for the current implementation since it only processes `data:` prefixed lines. **Not a bug, just non-spec-compliant for advanced SSE usage.**

#### High

3. **API keys sent over POST body in SSE/streaming requests** (see TypeScript section #1)
   `streamChat` and `streamAsk` send `api_key` in the request body. SSE responses are streamed, so the connection stays open. The API key in the body could be logged by middleware that buffers requests. Should use a custom header: `headers: { "x-api-key": settings.apiKey }`.

4. **No AbortSignal passed from chat store** (see TypeScript section #8)
   `streamChat` accepts `signal?: AbortSignal` but `useChatStore.send()` never passes one. The `DocumentsPage` correctly creates `AbortController`, but `ChatPage` can't cancel a streaming request.

#### Medium

5. **`readSSE` buffer handling could be more robust** (`api.ts:185-198`)
   The current buffer splitting by `\n` doesn't handle `\r\n` (Windows) line endings or chunked streams that split mid-line. The `buffer.indexOf("\n")` approach will leave `\r` at the end of lines, but `line.trim()` handles that. However, if a single JSON event is split across multiple TCP chunks, the `while` loop correctly buffers them. The real issue is if the buffer gets very large (no max size) — a malicious or buggy server could cause memory issues by sending a very long line without newlines. **Fix:** Add a max buffer size check.

6. **`streamAsk` in DocumentsPage doesn't handle the "done" event** (`DocumentsPage.tsx:84-96`)
   The SSE event handler has a `case "done": break;` that does nothing. Compare with the chat store which handles "done" by finalizing the assistant message. The RAG answer should be finalized on "done" (e.g., clear streaming state, mark as complete). Currently `setAskState("idle")` is called in `finally` so this is handled, but the "done" event is wasted.

---

## 10. State Management Issues

### Severity: 1 Critical, 2 High, 3 Medium

#### Critical

1. **React Query used inconsistently** — only 2 of 8 pages use it
   | Page | Fetch method | Query Client |
   |------|-------------|--------------|
   | `ChatPage` | `useQuery` (history) | ✅ |
   | `DocumentsPage` | `useQuery` (docs) | ✅ |
   | `BooksPage` | manual `useState` + `useEffect` | ❌ |
   | `ExamPage` | manual `useEffect` | ❌ |
   | `DiagnosticPage` | manual `useEffect` | ❌ |
   | `PluginsPage` | manual `useEffect` | ❌ |
   | `StudyTablePage` | manual async IIFE | ❌ |
   | `SettingsPage` | N/A (localStorage) | ❌ |

   **Fix:** Migrate `BooksPage`, `ExamPage`, `DiagnosticPage`, `PluginsPage` to use `useQuery` for consistency and automatic caching/revalidation.

#### High

2. **Zustand chat store uses negative `Date.now()` for temporary IDs** (`chat.ts:47,69,85`)
   ```ts
   const userMsg: Message = {
     id: -Date.now(),
     ...
   };
   ```
   If two messages are created in the same millisecond (user sends rapidly, or store processes an event and creates a temp message at the same time), IDs collide. The assistant messages also use `-Date.now()` (lines 69, 85). **Fix:** Use a counter-based ID generator: `let tempId = -1; const nextTempId = () => tempId--;`

3. **`loadSettings()` is not reactive** — settings are read from localStorage directly in component render (`DocumentsPage:27`, `BooksPage:206`, `ChatPage:152`). If the user navigates to Settings, changes a setting, and comes back, the setting won't update until the page reloads. React Query doesn't know about localStorage changes. **Fix:** Create a `useSettings()` hook that reads from localStorage and subscribes to storage events.

#### Medium

4. **`useChatStore` error cleanup is incomplete** (`chat.ts:109-119`)
   When an error event comes from SSE, the store sets `error` but doesn't clear it on the next successful send — actually, `send()` does `set({ error: null })` at the start (line 44), so it is cleared. ✅ Actually OK.

5. **`DocumentsPage` uses local state for error/streaming instead of store** — `setAskState("streaming")` and `setError` are local, while the chat store has the same patterns. This inconsistency means the DocumentsPage streaming state can't be shared with other components. **Minor** but architecturally inconsistent.

6. **`BooksPage` has 11 separate state variables** (`books`, `selected`, `lesson`, `error`, `busy`, `generating`, `searchQ`, `hits`, `importMsg`) — this is a state management smell. The page could benefit from `useReducer` or splitting into smaller components.

7. **`PluginsPage` has 6 separate state variables** (`plugins`, `error`, `busy`, `result`, `grades`, `subject`, `reportTopic`, `report`) — the `grades` and `subject` and `reportTopic` inputs are not debounced or validated. Entering a non-numeric grade value (`Number("abc")` → `NaN`) would produce `NaN` in the result.

---

## 11. API Client Analysis

### Severity: 1 High, 4 Medium

#### High

1. **No HTTP timeout handling** — all `fetch()` calls have no `AbortSignal` or timeout wrapper. If the backend hangs, the request will hang indefinitely (or until the browser's fetch timeout, which is ~300s). Should wrap with a timeout:
   ```ts
   const res = await fetch(url, {
     ...options,
     signal: AbortSignal.timeout(30000),
   });
   ```

#### Medium

2. **Inconsistent error message extraction** — `deleteConversation` uses `(await res.json().catch(() => null))?.detail` while `searchWeb` uses `await res.text().catch(() => "فشل البحث")`. The `deleteDocument` function uses `?.detail ?? "فشل الحذف"` but `indexDocument` uses `await res.text().catch(...)`. This inconsistency means some endpoints get JSON `detail` and others get raw text.

3. **No request/response logging or monitoring** — for a production app, there's no logging of failed requests, retry counts, or performance metrics. All errors are silent to the user (just shown as toast messages).

4. **`uploadDocument` progress is fake** (`api.ts:88-112`)
   ```ts
   onProgress?.(0);
   const res = await fetch("/api/documents", { ... });
   onProgress?.(100);
   ```
   The comment honestly says: "fetch لا يُبلّغ بالتقدم للبث الصعودي بدون axios". The progress goes 0 → 100 instantly. For a 10MB upload, this is misleading. Should use `ReadableStream` or `XMLHttpRequest` for real progress.

5. **No `credentials: "include"`** on any fetch call — if the backend uses cookie-based auth, all requests will fail. The app currently sends `api_key` in the body (see #1 above), so this is a design choice, but the lack of credential support limits authentication options.

---

## 12. File Upload Analysis

### Severity: 2 Medium

#### Medium

1. **`BooksPage` uses raw `<input type="file">` instead of `DragDropUpload`** (`BooksPage.tsx:396-402`)
   ```tsx
   <input type="file" multiple={false} onChange={onUpload} ... />
   ```
   The `DragDropUpload` component (with validation, progress, drag-and-drop) exists but is only used on `DocumentsPage`. The `BooksPage` has a simpler upload that doesn't validate type or size client-side. The label says "حتى 100MB" but `maxSize` isn't enforced on the input.

2. **`BooksPage.onImportQuiz` doesn't validate JSON structure** (`BooksPage.tsx:332`)
   ```ts
   const items = JSON.parse(await file.text());
   const r = await importQuizJson(bookId, items);
   ```
   No validation that `items` is an array of the expected shape. If the user imports a malformed file, the error from the API would be cryptic. Should validate with a schema (zod) before sending.

---

## 13. Charts (StudyChart.tsx)

### Severity: 2 Medium

#### Critical (orphaned)

1. **`StudyChart` is never imported or used anywhere** — it's a complete dead code component. It should either be:
   - Deleted if unused
   - Imported on the `StudyTablePage` or a new "progress" page

2. **No empty-state handling** (`StudyChart.tsx:37,40-63`)
   ```ts
   const maxValue = Math.max(...data.map((d) => d.score), 100);
   ```
   If `data` is empty, `Math.max(...[], 100)` = 100, which is correct. But `ResponsiveContainer` with `height={220}` will render an empty chart. Should handle `data.length === 0` with a fallback message.

#### Medium

3. **`Cell` color mapping uses `data[i]` instead of the loop index** (`StudyChart.tsx:55-59`)
   ```tsx
   {data.map((_, i) => (
     <Cell key={`cell-${i}`} fill={colors[Math.min(Math.floor(data[i].score / 34), 2)]} />
   ))}
   ```
   Uses `data[i]` inside the map callback — works because `i` is the index, but should use the destructured value: `data.map((d, i) => ... fill={colors[Math.min(Math.floor(d.score / 34), 2)]})`.

4. **Color threshold logic is undocumented** — scores 0-33 → red, 34-67 → amber, 68+ → green. The `/34` divisor makes this: `Math.floor(score / 34)` → 0, 1, 2. This works but is non-obvious. Should use explicit thresholds.

---

## 14. PWA / Service Worker

### Severity: 1 Medium

#### Medium

1. **`AppToaster` is rendered inside `ReloadPrompt`** (`ReloadPrompt.tsx:35`)
   ```tsx
   return (
     <>
       <AppToaster />
       {(offlineReady || needRefresh) && (...)}
     </>
   );
   ```
   While this ensures `AppToaster` is always available (since `ReloadPrompt` is always rendered in `App.tsx`), the architectural coupling is odd. `AppToaster` should be rendered at the root level, not inside the PWA prompt component. If someone refactors `ReloadPrompt`, they might accidentally remove the toaster.

2. **No offline fallback page** — PWA is configured for offline content but there's no offline fallback route or `index.html` cache strategy. If the user is offline and navigates to a new route, they'll get the browser's default offline page, not a custom one.

---

## 15. Summary: Issues by Category

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| TypeScript / Types | 3 | 5 | 8 | 0 | **16** |
| Performance | 1 | 3 | 4 | 0 | **8** |
| Accessibility | 1 | 4 | 6 | 2 | **13** |
| Responsive Design | 0 | 1 | 3 | 1 | **5** |
| RTL | 0 | 1 | 2 | 1 | **4** |
| Loading/Error States | 1 | 2 | 4 | 0 | **7** |
| SSE Streaming | 1 | 2 | 2 | 0 | **5** |
| State Management | 1 | 2 | 3 | 0 | **6** |
| API Client | 0 | 1 | 4 | 0 | **5** |
| File Upload | 0 | 0 | 2 | 0 | **2** |
| Charts | 1 | 0 | 3 | 0 | **4** |
| PWA | 0 | 0 | 1 | 0 | **1** |
| **Total** | **8** | **23** | **42** | **4** | **77** |

### Build/test/lint status
- ✅ `tsc --noEmit` — clean
- ✅ `vite build` — succeeds (6.07s, 856.90 kB JS)
- ✅ `vitest run` — 9/9 tests pass (5 files)
- ⚠️ `oxlint` — 1 warning (ThemeProvider exports)

### Top 5 priorities (critical, high-impact)
1. **Add code splitting** — bundle is 857 kB, single chunk (Critical)
2. **Fix `readSSE` JSON.parse error handling** — stream breaks on malformed JSON (Critical)
3. **Fix RTL message alignment** — user messages on wrong side (High)
4. **Add `aria-live` for streaming** — screen readers miss streamed content (Critical)
5. **Pass AbortSignal from chat store** — streaming can't be cancelled (High/Critical)
