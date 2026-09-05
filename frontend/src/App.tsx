import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'

import { PageSkeleton } from './components/PageSkeleton'
import { ReloadPrompt } from './components/ReloadPrompt'

// Route-level code splitting — كل صفحة في chunk مستقل (P4-240)
const ChatPage = lazy(() =>
  import('./pages/ChatPage').then((m) => ({ default: m.ChatPage })),
)
const DocumentsPage = lazy(() =>
  import('./pages/DocumentsPage').then((m) => ({ default: m.DocumentsPage })),
)
const PluginsPage = lazy(() =>
  import('./pages/PluginsPage').then((m) => ({ default: m.PluginsPage })),
)
const SettingsPage = lazy(() =>
  import('./pages/SettingsPage').then((m) => ({ default: m.SettingsPage })),
)
const StudyTablePage = lazy(() =>
  import('./pages/StudyTablePage').then((m) => ({ default: m.StudyTablePage })),
)
const BooksPage = lazy(() =>
  import('./pages/BooksPage').then((m) => ({ default: m.BooksPage })),
)
const ExamPage = lazy(() =>
  import('./pages/ExamPage').then((m) => ({ default: m.ExamPage })),
)
const DiagnosticPage = lazy(() =>
  import('./pages/DiagnosticPage').then((m) => ({ default: m.DiagnosticPage })),
)
const NotFoundPage = lazy(() =>
  import('./pages/NotFoundPage').then((m) => ({ default: m.NotFoundPage })),
)

export default function App() {
  return (
    <>
      <Suspense fallback={<PageSkeleton />}>
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/books" element={<BooksPage />} />
          <Route path="/exam" element={<ExamPage />} />
          <Route path="/diagnostic" element={<DiagnosticPage />} />
          <Route path="/plugins" element={<PluginsPage />} />
          <Route path="/plugins/study-table" element={<StudyTablePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
      <ReloadPrompt />
    </>
  )
}
