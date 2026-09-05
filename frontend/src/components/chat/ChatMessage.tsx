import { Bot, User } from 'lucide-react'

import { cn } from '../../lib/utils'
import type { Message } from '../../lib/api'
import { MathRenderer } from '../MathRenderer'

export function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  return (
    <div className={cn('flex gap-3', isUser ? 'justify-end' : 'justify-start')} aria-live="polite">
      {!isUser && (
        <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-indigo-600" aria-hidden="true">
          <Bot className="size-4 text-white" aria-hidden="true" />
        </div>
      )}
      <div
        className={cn(
          'max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap',
          isUser ? 'bg-slate-200 text-slate-900' : 'bg-indigo-600 text-white',
        )}
      >
        <MathRenderer content={message.content || '…'} />
      </div>
      {isUser && (
        <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-slate-200" aria-hidden="true">
          <User className="size-4 text-slate-600" aria-hidden="true" />
        </div>
      )}
    </div>
  )
}
