import { MessageSquarePlus, Settings } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { cn } from '../../lib/utils'
import type { Conversation } from '../../lib/api'

interface Props {
  conversations: Conversation[]
  currentId: number | null
  onNew: () => void
  onOpen: (id: number) => void
}

export function ConversationList({ conversations, currentId, onNew, onOpen }: Props) {
  const navigate = useNavigate()
  return (
    <aside className="flex w-64 shrink-0 flex-col border-l border-slate-200 bg-white">
      <div className="flex items-center justify-between p-4">
        <h1 className="text-lg font-bold">معلّمك</h1>
        <button
          onClick={onNew}
          title="محادثة جديدة"
          className="flex size-9 items-center justify-center rounded-full bg-indigo-600 text-white hover:bg-indigo-700"
        >
          <MessageSquarePlus className="size-4" />
        </button>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-2 pb-2">
        {conversations.map((c) => (
          <button
            key={c.id}
            onClick={() => onOpen(c.id)}
            className={cn(
              'block w-full truncate rounded-lg px-3 py-2 text-start text-sm transition',
              c.id === currentId ? 'bg-indigo-50 text-indigo-700' : 'text-slate-700 hover:bg-slate-100',
            )}
          >
            {c.title}
          </button>
        ))}
        {conversations.length === 0 && (
          <p className="px-3 py-4 text-center text-xs text-slate-400">لا توجد محادثات بعد</p>
        )}
      </nav>

      <button
        onClick={() => navigate('/settings')}
        className="flex items-center gap-2 border-t border-slate-200 px-4 py-3 text-sm text-slate-600 hover:bg-slate-50"
      >
        <Settings className="size-4" />
        الإعدادات
      </button>
    </aside>
  )
}
