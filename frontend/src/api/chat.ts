import { apiClient } from './client'
import type { ChatResponse, QueryHistoryEntry } from './types'

export interface ChatRequest {
  text: string
  connection_id: string
  session_id?: string
}

export const chatApi = {
  send: async (request: ChatRequest): Promise<ChatResponse> => {
    const { data } = await apiClient.post<ChatResponse>('/chat/', request)
    return data
  },

  history: async (connectionId: string, limit = 50): Promise<QueryHistoryEntry[]> => {
    const { data } = await apiClient.get<QueryHistoryEntry[]>('/chat/history', {
      params: { connection_id: connectionId, limit },
    })
    return data
  },
}
