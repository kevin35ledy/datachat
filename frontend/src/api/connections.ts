import { apiClient } from './client'
import type { ConnectionConfig, ConnectionCreate, ConnectionStatus, SchemaInfo, SchemaAnnotations, ClarificationResponse } from './types'

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

  getSchema: async (connId: string): Promise<SchemaInfo> => {
    const { data } = await apiClient.get<SchemaInfo>(`/connections/${connId}/schema`)
    return data
  },

  getAnnotations: async (connId: string): Promise<SchemaAnnotations> => {
    const { data } = await apiClient.get<SchemaAnnotations>(`/connections/${connId}/annotations`)
    return data
  },

  saveAnnotations: async (connId: string, annotations: SchemaAnnotations): Promise<SchemaAnnotations> => {
    const { data } = await apiClient.put<SchemaAnnotations>(`/connections/${connId}/annotations`, annotations)
    return data
  },

  clarify: async (connId: string, nlText: string): Promise<ClarificationResponse> => {
    const { data } = await apiClient.post<ClarificationResponse>(`/connections/${connId}/clarify`, { nl_text: nlText })
    return data
  },
}
