import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'

import { ChatInput } from '../components/chat/ChatInput'
import { ChatMessage } from '../components/chat/ChatMessage'
import { ConversationList } from '../components/chat/ConversationList'
import { fetchConversation, fetchHistory } from '../lib/api'
import { loadSettings } from '../lib/settings'
import { useChatStore } from '../store/chat'

export default function ChatPage() {
  const {
    conversations,
    setConversations,
    currentId,
    messages,
    streaming,
    error,
    openConversation,
    newConversation,
    send,
    stop,
    clearError,
  } = useChatStore()

  const bottomRef = useRef<HTMLDivElement>(null)

  useQuery({
    queryKey: ['history'],
    queryFn: async () => {
      const h = await fetchHistory()
      setConversations(h)
      return h
    },
  })

  const open = (id: number) => {
    fetchConversation(id).then((d) => openConversation(d.conversation.id, d.messages))
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex h-screen overflow-hidden bg-slate-100">
      <ConversationList
        conversations={conversations}
        currentId={currentId}
        onNew={newConversation}
        onOpen={open}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        <div className="flex-1 space-y-4 overflow-y-auto px-4 py-6" aria-live="polite">
          <div className="mx-auto max-w-3xl space-y-4">
            {messages.length === 0 && !streaming && (
              <div className="mt-16 text-center">
                <h2 className="text-xl font-bold text-slate-800">مرحباً بك في معلّمك 👋</h2>
                <p className="mt-2 text-sm text-slate-500">
                  اطرح سؤالك الدراسي — شرح، ملخص، تمارين محلولة… مع أي مزوّد تختاره من الإعدادات.
                </p>
              </div>
            )}
            {messages.map((m) => (
              <ChatMessage key={m.id} message={m} />
            ))}
            {error && (
              <div className="mx-auto max-w-3xl">
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {error}
                  <button onClick={clearError} className="mr-2 underline">
                    إغلاق
                  </button>
                </div>
              </div>
            )}
          </div>
          <div ref={bottomRef} />
        </div>

        <ChatInput
          disabled={streaming}
          onSend={(t) => send(t, loadSettings())}
          onStop={streaming ? stop : undefined}
          stopLabel="إيقاف"
        />
      </main>
    </div>
  )
}
