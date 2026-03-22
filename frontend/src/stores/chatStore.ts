import { create } from 'zustand'
import type { ChatResponse } from '../api/types'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  text: string
  response?: ChatResponse
  timestamp: Date
  isLoading?: boolean
}

interface ChatStore {
  sessions: Record<string, Message[]>
  activeSessionId: string
  isLoading: boolean

  getMessages: (sessionId: string) => Message[]
  addUserMessage: (sessionId: string, text: string) => string
  addAssistantMessage: (sessionId: string, messageId: string, response: ChatResponse) => void
  setLoading: (loading: boolean) => void
  clearSession: (sessionId: string) => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  sessions: {},
  activeSessionId: 'default',
  isLoading: false,

  getMessages: (sessionId) => get().sessions[sessionId] ?? [],

  addUserMessage: (sessionId, text) => {
    const id = crypto.randomUUID()
    const message: Message = {
      id,
      role: 'user',
      text,
      timestamp: new Date(),
    }
    set((state) => ({
      sessions: {
        ...state.sessions,
        [sessionId]: [...(state.sessions[sessionId] ?? []), message],
      },
    }))
    return id
  },

  addAssistantMessage: (sessionId, messageId, response) => {
    const message: Message = {
      id: messageId,
      role: 'assistant',
      text: response.summary || response.error || '',
      response,
      timestamp: new Date(),
    }
    set((state) => ({
      sessions: {
        ...state.sessions,
        [sessionId]: [...(state.sessions[sessionId] ?? []), message],
      },
    }))
  },

  setLoading: (isLoading) => set({ isLoading }),

  clearSession: (sessionId) =>
    set((state) => ({ sessions: { ...state.sessions, [sessionId]: [] } })),
}))
