import { useEffect, useState } from 'react'
import { ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { PROVIDERS, loadSettings, saveSettings, type ProviderSettings } from '../../lib/settings'

export function SettingsPanel() {
  const navigate = useNavigate()
  const [form, setForm] = useState<ProviderSettings>(loadSettings())
  const [saved, setSaved] = useState(false)

  const isCustom = form.provider === 'custom'
  const isOllama = form.provider === 'ollama'

  const update = <K extends keyof ProviderSettings>(key: K, value: ProviderSettings[K]) => {
    setForm((f) => ({ ...f, [key]: value }))
    setSaved(false)
  }

  useEffect(() => {
    if (!saved) return
    const t = setTimeout(() => setSaved(false), 2000)
    return () => clearTimeout(t)
  }, [saved])

  return (
    <div className="mx-auto max-w-xl px-6 py-10">
      <button
        onClick={() => navigate('/')}
        className="mb-6 flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800"
      >
        <ArrowRight className="size-4" />
        العودة للدردشة
      </button>

      <h1 className="text-2xl font-bold">الإعدادات</h1>
      <p className="mt-1 text-sm text-slate-500">
        اختر مزوّد النموذج — محلي (Ollama) أو سحابي. المفاتيح تبقى في متصفحك ولا تُخزَّن على الخادم.
      </p>

      <form
        className="mt-8 space-y-6"
        onSubmit={(e) => {
          e.preventDefault()
          saveSettings(form)
          setSaved(true)
        }}
      >
        <label className="block">
          <span className="mb-1 block text-sm font-medium">المزوّد</span>
          <select
            value={form.provider}
            onChange={(e) => update('provider', e.target.value)}
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
          >
            {PROVIDERS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
          <span className="mt-1 block text-xs text-slate-400">
            {PROVIDERS.find((p) => p.id === form.provider)?.hint}
          </span>
        </label>

        <label className="block">
          <span className="mb-1 block text-sm font-medium">النموذج</span>
          <input
            value={form.model}
            onChange={(e) => update('model', e.target.value)}
            dir="ltr"
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
            placeholder="qwen2.5:7b"
          />
        </label>

        {(isCustom || isOllama) && (
          <label className="block">
            <span className="mb-1 block text-sm font-medium">
              {isCustom ? 'عنوان الخادم (base_url)' : 'عنوان Ollama'}
            </span>
            <input
              value={form.baseUrl ?? ''}
              onChange={(e) => update('baseUrl', e.target.value)}
              dir="ltr"
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              placeholder="http://localhost:11434"
            />
          </label>
        )}

        {!isOllama && (
          <label className="block">
            <span className="mb-1 block text-sm font-medium">مفتاح API</span>
            <input
              type="password"
              value={form.apiKey ?? ''}
              onChange={(e) => update('apiKey', e.target.value)}
              dir="ltr"
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              placeholder={isCustom ? 'sk-… (اختياري)' : 'sk-…'}
            />
            <span className="mt-1 block text-xs text-slate-400">
              يُرسل مع الطلب فقط — لا يُحفظ في الخادم أو قاعدة البيانات
            </span>
          </label>
        )}

        <button
          type="submit"
          className="w-full rounded-xl bg-indigo-600 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700"
        >
          {saved ? '✓ تم الحفظ' : 'حفظ الإعدادات'}
        </button>
      </form>
    </div>
  )
}
