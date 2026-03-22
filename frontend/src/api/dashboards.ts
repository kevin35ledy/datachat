import { apiClient } from './client'
import type {
  Dashboard,
  DashboardCreate,
  DashboardUpdate,
  AddWidgetRequest,
  DashboardRefreshResult,
} from './types'

export const dashboardsApi = {
  list: (): Promise<Dashboard[]> =>
    apiClient.get('/dashboards/').then(r => r.data),

  create: (payload: DashboardCreate): Promise<Dashboard> =>
    apiClient.post('/dashboards/', payload).then(r => r.data),

  get: (id: string): Promise<Dashboard> =>
    apiClient.get(`/dashboards/${id}`).then(r => r.data),

  update: (id: string, payload: DashboardUpdate): Promise<Dashboard> =>
    apiClient.put(`/dashboards/${id}`, payload).then(r => r.data),

  delete: (id: string): Promise<void> =>
    apiClient.delete(`/dashboards/${id}`).then(() => undefined),

  addWidgetFromNL: (id: string, payload: AddWidgetRequest): Promise<Dashboard> =>
    apiClient.post(`/dashboards/${id}/widgets/from-nl`, payload).then(r => r.data),

  removeWidget: (dashboardId: string, widgetId: string): Promise<Dashboard> =>
    apiClient.delete(`/dashboards/${dashboardId}/widgets/${widgetId}`).then(r => r.data),

  refresh: (id: string): Promise<DashboardRefreshResult> =>
    apiClient.post(`/dashboards/${id}/refresh`).then(r => r.data),
}
