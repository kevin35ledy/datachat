import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Eye, Check } from 'lucide-react'
import { dashboardsApi } from '../api/dashboards'
import { connectionsApi } from '../api/connections'
import { useDashboardStore } from '../stores/dashboardStore'
import { DashboardGrid } from '../components/dashboard/DashboardGrid'
import { AddWidgetPanel } from '../components/dashboard/AddWidgetPanel'
import type { Dashboard, DashboardWidget, QueryResult, WidgetType, WidgetConfig } from '../api/types'

export function DashboardBuilderPage() {
  const { dashboardId } = useParams<{ dashboardId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { widgetResults, widgetLoading, setAllWidgetResults, setWidgetResult, setWidgetLoading } = useDashboardStore()

  const [isAddingWidget, setIsAddingWidget] = useState(false)
  const [saved, setSaved] = useState(false)
  const [widgetWarnings, setWidgetWarnings] = useState<string[]>([])
  const [widgetRegenerating, setWidgetRegenerating] = useState<Record<string, boolean>>({})

  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['dashboard', dashboardId],
    queryFn: () => dashboardsApi.get(dashboardId!),
    enabled: !!dashboardId,
  })

  // Refresh widget data on load
  useEffect(() => {
    if (dashboard?.widgets.length) {
      refreshAll(dashboard)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dashboard?.id])

  const refreshAll = async (d: Dashboard) => {
    if (!d.id || !d.widgets.length) return
    const result = await dashboardsApi.refresh(d.id)
    const mapped: Record<string, QueryResult | string> = {}
    for (const r of result.results) {
      mapped[r.widget_id] = r.error ?? r.result ?? 'Aucun résultat'
    }
    setAllWidgetResults(mapped)
  }

  const flashSaved = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleAddWidget = async (nlText: string, widgetType: WidgetType) => {
    if (!dashboardId) return
    setIsAddingWidget(true)
    setWidgetWarnings([])
    try {
      const { dashboard: updated, warnings } = await dashboardsApi.addWidgetFromNL(dashboardId, { nl_text: nlText, widget_type: widgetType })
      setWidgetWarnings(warnings)
      qc.setQueryData(['dashboard', dashboardId], updated)

      // Refresh only the new widget
      const newWidget = updated.widgets[updated.widgets.length - 1]
      if (newWidget) {
        setWidgetLoading(newWidget.id, true)
        try {
          const refreshed = await dashboardsApi.refresh(dashboardId)
          for (const r of refreshed.results) {
            if (r.widget_id === newWidget.id) {
              setWidgetResult(r.widget_id, r.error ?? r.result ?? 'Aucun résultat')
            }
          }
        } finally {
          setWidgetLoading(newWidget.id, false)
        }
      }
      flashSaved()
    } finally {
      setIsAddingWidget(false)
    }
  }

  const handleDeleteWidget = async (widgetId: string) => {
    if (!dashboardId) return
    const updated = await dashboardsApi.removeWidget(dashboardId, widgetId)
    qc.setQueryData(['dashboard', dashboardId], updated)
    flashSaved()
  }

  const handleMoveWidget = async (widgetId: string, dir: 'up' | 'down') => {
    if (!dashboard || !dashboardId) return
    const sorted = [...dashboard.widgets].sort((a, b) => a.position - b.position)
    const idx = sorted.findIndex(w => w.id === widgetId)
    if (idx === -1) return
    const swapIdx = dir === 'up' ? idx - 1 : idx + 1
    if (swapIdx < 0 || swapIdx >= sorted.length) return

    const reordered: DashboardWidget[] = sorted.map((w, i) => {
      if (i === idx) return { ...w, position: sorted[swapIdx].position }
      if (i === swapIdx) return { ...w, position: sorted[idx].position }
      return w
    })

    const updated = await dashboardsApi.update(dashboardId, { widgets: reordered })
    qc.setQueryData(['dashboard', dashboardId], updated)
    flashSaved()
  }

  const handleConfigChange = async (widgetId: string, config: WidgetConfig) => {
    if (!dashboardId) return
    const updated = await dashboardsApi.updateWidgetConfig(dashboardId, widgetId, config)
    qc.setQueryData(['dashboard', dashboardId], updated)
  }

  const handleRegenerateWidget = async (widgetId: string, nlText: string) => {
    if (!dashboardId) return
    setWidgetRegenerating(prev => ({ ...prev, [widgetId]: true }))
    try {
      const { dashboard: updated, warnings } = await dashboardsApi.regenerateWidget(dashboardId, widgetId, { nl_text: nlText })
      setWidgetWarnings(warnings)
      qc.setQueryData(['dashboard', dashboardId], updated)
      const refreshed = await dashboardsApi.refresh(dashboardId)
      for (const r of refreshed.results) {
        if (r.widget_id === widgetId) {
          setWidgetResult(r.widget_id, r.error ?? r.result ?? 'Aucun résultat')
        }
      }
      flashSaved()
    } finally {
      setWidgetRegenerating(prev => ({ ...prev, [widgetId]: false }))
    }
  }

  const handleResizeWidget = async (widgetId: string, newWidth: 1 | 2 | 3) => {
    if (!dashboard || !dashboardId) return
    const widgets = dashboard.widgets.map(w =>
      w.id === widgetId ? { ...w, width: newWidth } : w
    )
    const updated = await dashboardsApi.update(dashboardId, { widgets })
    qc.setQueryData(['dashboard', dashboardId], updated)
    flashSaved()
  }

  if (isLoading) {
    return <div className="p-6 animate-pulse h-32 bg-gray-800 rounded-xl m-6" />
  }

  if (!dashboard) {
    return <div className="p-6 text-red-400">Tableau de bord introuvable.</div>
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-4 px-6 py-4 border-b border-gray-800 shrink-0">
        <button onClick={() => navigate('/dashboards')} className="btn-ghost p-1.5 rounded-lg">
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h1 className="text-base font-semibold text-gray-100 truncate">Éditer — {dashboard.name}</h1>
            {saved && (
              <span className="flex items-center gap-1 text-xs text-green-400">
                <Check size={12} /> Sauvegardé
              </span>
            )}
          </div>
        </div>
        <button
          onClick={() => navigate(`/dashboards/${dashboard.id}`)}
          className="btn-ghost flex items-center gap-2 px-3 py-2"
        >
          <Eye size={15} />
          Voir
        </button>
      </div>

      {/* Body */}
      <div className="flex flex-1 min-h-0">
        {/* Sidebar */}
        <div className="w-72 shrink-0 border-r border-gray-800 p-4 overflow-y-auto">
          <AddWidgetPanel
            connectionId={dashboard.connection_id}
            onAdd={handleAddWidget}
            onClarify={(nlText) => connectionsApi.clarify(dashboard.connection_id, nlText).then(r => r.questions)}
            isLoading={isAddingWidget}
            warnings={widgetWarnings}
          />

          {dashboard.widgets.length > 0 && (
            <div className="mt-6">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Widgets ({dashboard.widgets.length})
              </p>
              <div className="flex flex-col gap-2">
                {[...dashboard.widgets]
                  .sort((a, b) => a.position - b.position)
                  .map(w => (
                    <div key={w.id} className="flex items-center gap-2 text-xs text-gray-400 bg-gray-800/50 rounded-lg px-3 py-2">
                      <span className="flex-1 truncate">{w.title}</span>
                      <span className="text-gray-600 shrink-0">{w.widget_type}</span>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>

        {/* Canvas */}
        <div className="flex-1 overflow-y-auto p-6">
          <DashboardGrid
            widgets={dashboard.widgets}
            widgetResults={widgetResults}
            widgetLoading={widgetLoading}
            widgetRegenerating={widgetRegenerating}
            isEditing
            onDeleteWidget={handleDeleteWidget}
            onMoveWidget={handleMoveWidget}
            onResizeWidget={handleResizeWidget}
            onRegenerateWidget={handleRegenerateWidget}
            onConfigChange={handleConfigChange}
          />
        </div>
      </div>
    </div>
  )
}
