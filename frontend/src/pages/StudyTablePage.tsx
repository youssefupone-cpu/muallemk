import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

import { fetchPluginStorage, fetchPlugins, savePluginStorage, type PluginItem } from '../lib/api'
import { errMsg } from '../lib/utils'

interface FieldSpec {
  key: string
  label: string
  enum?: string[]
}

interface PluginUiItem extends PluginItem {
  ui?: { schema?: { items?: { properties?: Record<string, { type?: string; enum?: string[] }> } } }
}

export default function StudyTablePage() {
  const [plugin, setPlugin] = useState<PluginItem | null>(null)
  const [fields, setFields] = useState<FieldSpec[]>([])
  const [rows, setRows] = useState<Record<string, string>[]>([])
  const [draft, setDraft] = useState<Record<string, string>>({})
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  // React Query — تحميل قائمة الإضافات مع كاش (P4-240)
  const qc = useQuery({
    queryKey: ['plugins'],
    queryFn: fetchPlugins,
    staleTime: 1000 * 60 * 2,
    retry: 2,
  })

  useEffect(() => {
    if (qc.isError) setError(errMsg(qc.error))
    if (qc.data) {
      const plugins = qc.data
      const p = plugins.find((x) => x.name === 'study-table') ?? null
      setPlugin(p)
      if (p) {
        const spec = (p as PluginUiItem).ui?.schema?.items?.properties
        if (spec) {
          setFields(
            Object.entries(spec).map(([k, v]) => ({
              key: k,
              label: k === 'subject' ? 'المادة' : k === 'time' ? 'الوقت' : k,
              enum: v.enum,
            })),
          )
        }
        void fetchPluginStorage('study-table').then((stored) => {
          setRows(stored.items ?? [])
        }).catch((e) => setError(errMsg(e)))
      }
    }
  }, [qc.data, qc.isError, qc.error])

  const addRow = () => {
    if (!draft.day || !draft.subject) return
    const next = [...rows, { ...draft }]
    setRows(next)
    void persist(next)
    const { day: _day, ...rest } = draft
    setDraft({ ...rest })
  }

  const removeRow = (i: number) => {
    const next = rows.filter((_, idx) => idx !== i)
    setRows(next)
    void persist(next)
  }

  const persist = async (next: Record<string, string>[]) => {
    setSaving(true)
    setError('')
    try {
      await savePluginStorage('study-table', next)
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setSaving(false)
    }
  }

  const dayField = fields.find((f) => f.key === 'day')
  const textFields = fields.filter((f) => f.key !== 'day')

  return (
    <div dir="rtl" className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-4xl p-6">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold">{plugin?.title ?? 'جدول الدراسة'}</h1>
          <div className="flex gap-2">
            <Link to="/" className="rounded-lg bg-slate-200 px-4 py-2 text-sm hover:bg-slate-300">
              المحادثة
            </Link>
            <Link to="/documents" className="rounded-lg bg-slate-200 px-4 py-2 text-sm hover:bg-slate-300">
              مستنداتي
            </Link>
            <Link to="/plugins" className="rounded-lg bg-slate-200 px-4 py-2 text-sm hover:bg-slate-300">
              الإضافات
            </Link>
          </div>
        </div>

        {error && <div className="mb-4 rounded-lg bg-red-100 p-3 text-sm text-red-800">{error}</div>}
        {plugin && <p className="mb-4 text-sm text-slate-600">{plugin.description}</p>}

        <div className="mb-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-end gap-2">
            {dayField?.enum && (
              <label className="text-sm">
                اليوم
                <select
                  value={draft.day ?? ''}
                  onChange={(e) => setDraft((d) => ({ ...d, day: e.target.value }))}
                  className="mt-1 block rounded-lg border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="">اختر</option>
                  {dayField.enum.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {textFields.map((f) => (
              <label key={f.key} className="block">
                {f.label}
                <input
                  value={draft[f.key] ?? ''}
                  onChange={(e) => setDraft((d) => ({ ...d, [f.key]: e.target.value }))}
                  placeholder={f.key === 'time' ? 'مثال 09:00' : 'مثال: الرياضيات'}
                  className="mt-1 block rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </label>
            ))}
            <button
              onClick={addRow}
              disabled={!draft.day || !draft.subject}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-40"
            >
              أضف
            </button>
            {saving && <span className="text-xs text-slate-400">جارٍ الحفظ…</span>}
          </div>
        </div>

        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-right">
              <tr>
                {dayField && <th className="px-4 py-2 font-medium text-slate-600">اليوم</th>}
                {textFields.map((f) => (
                  <th key={f.key} className="px-4 py-2 font-medium text-slate-600">
                    {f.label}
                  </th>
                ))}
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr>
                  <td colSpan={textFields.length + 2} className="px-4 py-6 text-center text-slate-400">
                    لا صفوف — أضف حصتك الأولى.
                  </td>
                </tr>
              )}
              {rows.map((r, i) => (
                <tr key={i} className="border-t border-slate-100">
                  <td className="px-4 py-2">{r.day}</td>
                  {textFields.map((f) => (
                    <td key={f.key} className="px-4 py-2">
                      {r[f.key] ?? ''}
                    </td>
                  ))}
                  <td className="px-4 py-2 text-left">
                    <button
                      onClick={() => removeRow(i)}
                      className="text-xs text-red-500 hover:text-red-700"
                    >
                      حذف
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <details className="mt-4 rounded-lg bg-slate-100 p-3 text-xs text-slate-500">
          <summary className="cursor-pointer font-medium">تفاصيل تقنية (UI تصريحي)</summary>
          <p className="mt-2">
            هذه الصفحة تُرسم تلقائياً من <code>ui.schema</code> المُعلن في manifest.json لإضافة{' '}
            <code>study-table</code> — لا React مكتوب في الإضافة. الحفظ عبر
            <code>PluginContext.data/ui.json</code> (تخزين معزول).
          </p>
        </details>
      </div>
    </div>
  )
}