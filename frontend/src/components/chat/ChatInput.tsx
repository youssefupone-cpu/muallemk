import { useState, type FormEvent } from 'react'
import { Loader2, SendHorizonal } from 'lucide-react'

import { cn } from '../../lib/utils'

interface Props {
  disabled?: boolean
  onSend: (text: string) => void
}

export function ChatInput({ disabled, onSend }: Props) {
  const [text, setText] = useState('')

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setText('')
  }

  return (
    <form onSubmit={submit} className="border-t border-slate-200 bg-white p-4">
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submit(e as unknown as FormEvent)
            }
          }}
          rows={1}
          placeholder="اكتب سؤالك الدراسي… (Enter للإرسال، Shift+Enter لسطر جديد)"
          className={cn(
            'max-h-40 flex-1 resize-none rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm',
            'focus:border-indigo-500 focus:bg-white focus:outline-none',
          )}
        />
        <button
          type="submit"
          disabled={disabled || !text.trim()}
          className="flex size-11 items-center justify-center rounded-full bg-indigo-600 text-white transition hover:bg-indigo-700 disabled:opacity-40"
        >
          {disabled ? <Loader2 className="size-5 animate-spin" /> : <SendHorizonal className="size-5" />}
        </button>
      </div>
    </form>
  )
}
