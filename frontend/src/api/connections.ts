import { apiClient } from './client'
import type { ConnectionConfig, ConnectionCreate, ConnectionStatus } from './types'

export const connectionsApi = {
  list: async (): Promise<ConnectionConfig[]> => {
    const { data } = await apiClient.get<ConnectionConfig[]>('/connections/')
    return data
  },

  create: async (payload: ConnectionCreate): Promise<ConnectionConfig> => {
    const { data } = await apiClient.post<ConnectionConfig>('/connections/', payload)
    return data
  },

  test: async (connId: string): Promise<ConnectionStatus> => {
    const { data } = await apiClient.post<ConnectionStatus>(`/connections/${connId}/test`)
    return data
  },

  delete: async (connId: string): Promise<void> => {
    await apiClient.delete(`/connections/${connId}`)
  },
}
