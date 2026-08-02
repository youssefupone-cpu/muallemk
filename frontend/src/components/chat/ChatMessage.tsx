import { Bot, User } from 'lucide-react'

import { cn } from '../../lib/utils'
import type { Message } from '../../lib/api'

export function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  return (
    <div className={cn('flex gap-3', isUser ? 'justify-start' : 'justify-end')}>
      {isUser && (
        <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-slate-200">
          <User className="size-4 text-slate-600" />
        </div>
      )}
      <div
        className={cn(
          'max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap',
          isUser ? 'bg-slate-200 text-slate-900' : 'bg-indigo-600 text-white',
        )}
      >
        {message.content || '…'}
      </div>
      {!isUser && (
        <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-indigo-600">
          <Bot className="size-4 text-white" />
        </div>
      )}
    </div>
  )
}
