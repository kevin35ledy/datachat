import { create } from 'zustand'
import type { Dashboard, QueryResult } from '../api/types'

interface DashboardStore {
  dashboards: Dashboard[]
  activeDashboardId: string | null
  widgetResults: Record<string, QueryResult | string>
  widgetLoading: Record<string, boolean>

  setDashboards: (dashboards: Dashboard[]) => void
  addDashboard: (dashboard: Dashboard) => void
  updateDashboard: (dashboard: Dashboard) => void
  removeDashboard: (id: string) => void
  setActiveDashboard: (id: string | null) => void
  setWidgetResult: (widgetId: string, result: QueryResult | string) => void
  setWidgetLoading: (widgetId: string, loading: boolean) => void
  setAllWidgetResults: (results: Record<string, QueryResult | string>) => void
  clearWidgetResults: () => void
}

export const useDashboardStore = create<DashboardStore>((set) => ({
  dashboards: [],
  activeDashboardId: null,
  widgetResults: {},
  widgetLoading: {},

  setDashboards: (dashboards) => set({ dashboards }),

  addDashboard: (dashboard) =>
    set((s) => ({ dashboards: [...s.dashboards, dashboard] })),

  updateDashboard: (dashboard) =>
    set((s) => ({
      dashboards: s.dashboards.map((d) => (d.id === dashboard.id ? dashboard : d)),
    })),

  removeDashboard: (id) =>
    set((s) => ({
      dashboards: s.dashboards.filter((d) => d.id !== id),
      activeDashboardId: s.activeDashboardId === id ? null : s.activeDashboardId,
    })),

  setActiveDashboard: (id) => set({ activeDashboardId: id }),

  setWidgetResult: (widgetId, result) =>
    set((s) => ({ widgetResults: { ...s.widgetResults, [widgetId]: result } })),

  setWidgetLoading: (widgetId, loading) =>
    set((s) => ({ widgetLoading: { ...s.widgetLoading, [widgetId]: loading } })),

  setAllWidgetResults: (results) => set({ widgetResults: results }),

  clearWidgetResults: () => set({ widgetResults: {}, widgetLoading: {} }),
}))
