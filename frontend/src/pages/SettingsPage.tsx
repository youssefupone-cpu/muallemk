import { AppLayout } from '../components/layout/AppLayout'
import { SettingsPanel } from '../components/settings/SettingsPanel'

export function SettingsPage() {
  return (
    <AppLayout>
      <div className="mx-auto max-w-2xl p-6">
        <h1 className="mb-4 text-2xl font-bold">الإعدادات</h1>
        <SettingsPanel />
      </div>
    </AppLayout>
  )
}
