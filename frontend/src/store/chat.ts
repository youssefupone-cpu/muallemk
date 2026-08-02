import { create } from 'zustand'

import { streamChat, type ChatEvent, type Conversation, type Message } from '../lib/api'

interface ChatState {
  conversations: Conversation[]
  currentId: number | null
  messages: Message[]
  streaming: boolean
  error: string | null
  setConversations: (c: Conversation[]) => void
  openConversation: (id: number, messages: Message[]) => void
  newConversation: () => void
  send: (text: string, settings: Parameters<typeof streamChat>[2]) => Promise<void>
  clearError: () => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  currentId: null,
  messages: [],
  streaming: false,
  error: null,

  setConversations: (c) => set({ conversations: c }),
  openConversation: (id, messages) => set({ currentId: id, messages, error: null }),
  newConversation: () => set({ currentId: null, messages: [], error: null }),

  clearError: () => set({ error: null }),

  send: async (text, settings) => {
    if (get().streaming) return
    set({ streaming: true, error: null })

    // رسالة المستخدم تظهر فوراً
    const userMsg: Message = {
      id: -Date.now(),
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    }
    set({ messages: [...get().messages, userMsg] })

    let assistantContent = ''
    const onEvent = (e: ChatEvent) => {
      if (e.type === 'conversation') {
        set({ currentId: e.id ?? null })
      } else if (e.type === 'delta') {
        assistantContent += e.content ?? ''
        const st = get()
        const msgs = [...st.messages]
        const last = msgs[msgs.length - 1]
        if (last && last.role === 'assistant') {
          msgs[msgs.length - 1] = { ...last, content: assistantContent }
        } else {
          msgs.push({
            id: -Date.now(),
            role: 'assistant',
            content: assistantContent,
            created_at: new Date().toISOString(),
          })
        }
        set({ messages: msgs })
      } else if (e.type === 'done' && e.content) {
        assistantContent = e.content
        const st = get()
        const msgs = [...st.messages]
        const last = msgs[msgs.length - 1]
        if (last && last.role === 'assistant') {
          msgs[msgs.length - 1] = { ...last, content: e.content }
        }
        set({ messages: msgs })
      } else if (e.type === 'error') {
        set({ error: e.detail ?? 'حدث خطأ غير متوقع' })
      }
    }

    try {
      await streamChat(text, get().currentId, settings, onEvent)
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'تعذّر الاتصال بالخادم' })
    } finally {
      set({ streaming: false })
    }
  },
}))
