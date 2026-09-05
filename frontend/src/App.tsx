import { Route, Routes } from 'react-router-dom'
import { lazy, Suspense } from 'react'

import { ReloadPrompt } from './components/ReloadPrompt'
import { PageSkeleton } from './components/PageSkeleton'

// Route-level code splitting — كل صفحة في chunk مستقل (P4-240)
const ChatPage = lazy(() => import('./pages/ChatPage'))
const DocumentsPage = lazy(() => import('./pages/DocumentsPage'))
const PluginsPage = lazy(() => import('./pages/PluginsPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))
const StudyTablePage = lazy(() => import('./pages/StudyTablePage'))

export default function App() {
  return (
    <>
      <Suspense fallback={<PageSkeleton />}>
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/plugins" element={<PluginsPage />} />
          <Route path="/plugins/study-table" element={<StudyTablePage />} />
        </Routes>
      </Suspense>
      <ReloadPrompt />
    </>
  )
}
