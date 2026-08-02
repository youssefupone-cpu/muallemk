import { Route, Routes } from 'react-router-dom'

import { ChatPage } from './pages/ChatPage'
import { DocumentsPage } from './pages/DocumentsPage'
import { PluginsPage } from './pages/PluginsPage'
import { SettingsPage } from './pages/SettingsPage'
import { StudyTablePage } from './pages/StudyTablePage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<ChatPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="/documents" element={<DocumentsPage />} />
      <Route path="/plugins" element={<PluginsPage />} />
      <Route path="/plugins/study-table" element={<StudyTablePage />} />
    </Routes>
  )
}