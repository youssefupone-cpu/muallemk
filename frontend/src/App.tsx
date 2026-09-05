import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'

import { PageSkeleton } from './components/PageSkeleton'
import { ReloadPrompt } from './components/ReloadPrompt'

// Route-level code splitting — default exports تتكامل مباشرة مع React.lazy
const ChatPage = lazy(() => import('./pages/ChatPage'))
const DocumentsPage = lazy(() => import('./pages/DocumentsPage'))
const PluginsPage = lazy(() => import('./pages/PluginsPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))
const StudyTablePage = lazy(() => import('./pages/StudyTablePage'))
const BooksPage = lazy(() => import('./pages/BooksPage'))
const ExamPage = lazy(() => import('./pages/ExamPage'))
const DiagnosticPage = lazy(() => import('./pages/DiagnosticPage'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'))

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
