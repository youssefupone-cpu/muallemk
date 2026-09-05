import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

import {
  fetchDocuments,
  indexDocument,
  streamAsk,
  uploadDocument,
  type AskEvent,
  type RAGSource,
} from '../lib/api'
import { loadSettings } from '../lib/settings'
import { errMsg, isAbortError } from '../lib/utils'

export default function DocumentsPage() {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const [indexing, setIndexing] = useState<Record<number, boolean>>({})
  const settings = loadSettings()

  const [question, setQuestion] = useState('')
  const [askState, setAskState] = useState<'idle' | 'streaming'>('idle')
  const [answer, setAnswer] = useState('')
  const [sources, setSources] = useState<RAGSource[]>([])
  const abortRef = useRef<AbortController | null>(null)

  // React Query — تحميل المستندات مع كاش (P4-240)
  const qc = useQuery({
    queryKey: ['documents'],
    queryFn: fetchDocuments,
    staleTime: 1000 * 60 * 2,
    retry: 2,
  })

  const docs = qc.data ?? []
  useEffect(() => { if (qc.isError) setError(errMsg(qc.error)) }, [qc.isError, qc.error])
  const invalidate = () => { void qc.refetch() }

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setBusy('upload')
    setError('')
    try {
      await uploadDocument(file)
      invalidate()
    } catch (err) {
      setError(errMsg(err))
    } finally {
      setBusy('')
      e.target.value = ''
    }
  }

  const onIndex = async (id: number) => {
    setIndexing((s) => ({ ...s, [id]: true }))
    setError('')
    try {
      const r = await indexDocument(id)
      invalidate()
      if (import.meta.env.DEV) console.info(`indexed ${r.indexed} chunks`)
    } catch (err) {
      setError(errMsg(err))
    } finally {
      setIndexing((s) => ({ ...s, [id]: false }))
    }
  }

  const ask = async () => {
    if (!question.trim() || askState === 'streaming') return
    setAskState('streaming')
    setAnswer('')
    setSources([])
    setError('')
    abortRef.current = new AbortController()
    try {
      await streamAsk(question, null, settings, (ev: AskEvent) => {
        switch (ev.type) {
          case 'sources':
            setSources(ev.sources ?? [])
            break
          case 'delta':
            setAnswer((a) => a + (ev.content ?? ''))
            break
          case 'done':
            break
          case 'error':
            setError(ev.detail ?? 'خطأ في الإجابة')
            break
        }
      }, abortRef.current.signal)
    } catch (err) {
      if (!isAbortError(err)) {
        setError(errMsg(err))
      }
    } finally {
      setAskState('idle')
    }
  }

  return (
    <div dir="rtl" className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-4xl p-6">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold">مستنداتي</h1>
          <div className="flex gap-2">
            <Link to="/" className="rounded-lg bg-slate-200 px-4 py-2 text-sm hover:bg-slate-300">
              المحادثة
            </Link>
            <Link to="/documents" className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700">
              مستنداتي
            </Link>
            <Link to="/plugins" className="rounded-lg bg-slate-200 px-4 py-2 text-sm hover:bg-slate-300">
              الإضافات
            </Link>
          </div>
        </div>

        {error && <div className="mb-4 rounded-lg bg-red-100 p-3 text-sm text-red-800">{error}</div>}

        <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <label className="block text-sm font-medium text-slate-700">رفع ملف (PDF/Word/نص/صورة OCR)</label>
          <input type="file" onChange={onUpload} disabled={busy === 'upload'} className="mt-2 block w-full text-sm" />
        </div>

        <div className="space-y-3">
          {docs.length === 0 && <p className="text-sm text-slate-500">لا مستندات بعد — ارفع كتاباً أو مذكرة.</p>}
          {docs.map((d) => (
            <div key={d.id} className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div>
                <h2 className="font-medium">{d.filename}</h2>
                <p className="text-xs text-slate-500">
                  {d.file_type} · {new Date(d.created_at).toLocaleDateString('ar')}
                </p>
              </div>
              <button
                onClick={() => onIndex(d.id)}
                disabled={indexing[d.id]}
                className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {indexing[d.id] ? 'جارٍ الفهرسة…' : 'فهرسة للأسئلة'}
              </button>
            </div>
          ))}
        </div>

        <div className="mt-8 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="mb-3 font-semibold">اسأل كتابك</h2>
          <div className="flex gap-2">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="مثال: ما أهمية التجارة في الحضارة الإسلامية؟"
              rows={2}
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            <button
              onClick={ask}
              disabled={askState === 'streaming' || !question.trim()}
              className="rounded-lg bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700 disabled:opacity-50"
            >
              {askState === 'streaming' ? '…' : 'اسأل'}
            </button>
          </div>
          {answer && (
            <div className="mt-3 rounded-lg bg-slate-50 p-3">
              <p className="whitespace-pre-wrap text-sm leading-7">{answer}</p>
            </div>
          )}
          {sources.length > 0 && (
            <div className="mt-3">
              <p className="mb-1 text-xs font-medium text-slate-500">المصادر:</p>
              <ul className="space-y-1 text-xs text-slate-600">
                {sources.slice(0, 5).map((s, i) => (
                  <li key={i}>
                    [{i + 1}] <span className="font-medium">{s.filename}</span>
                    {s.heading ? ` — ${s.heading}` : ''} · درجة {s.score.toFixed(2)}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}