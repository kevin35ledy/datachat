import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Edit2, RefreshCw, ArrowLeft } from 'lucide-react'
import { dashboardsApi } from '../api/dashboards'
import { useDashboardStore } from '../stores/dashboardStore'
import { DashboardGrid } from '../components/dashboard/DashboardGrid'
import type { QueryResult } from '../api/types'

export function DashboardViewPage() {
  const { dashboardId } = useParams<{ dashboardId: string }>()
  const navigate = useNavigate()
  const { widgetResults, widgetLoading, setAllWidgetResults } = useDashboardStore()
  const [isRefreshing, setIsRefreshing] = useState(false)

  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['dashboard', dashboardId],
    queryFn: () => dashboardsApi.get(dashboardId!),
    enabled: !!dashboardId,
  })

  const refresh = async () => {
    if (!dashboardId || isRefreshing) return
    setIsRefreshing(true)
    try {
      const result = await dashboardsApi.refresh(dashboardId)
      const mapped: Record<string, QueryResult | string> = {}
      for (const r of result.results) {
        mapped[r.widget_id] = r.error ?? r.result ?? 'Aucun résultat'
      }
      setAllWidgetResults(mapped)
    } finally {
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    if (dashboard?.widgets.length) {
      refresh()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dashboard?.id])

  if (isLoading) {
    return (
      <div className="p-6 flex flex-col gap-4 animate-pulse">
        <div className="h-8 bg-gray-800 rounded w-1/3" />
        <div className="grid grid-cols-12 gap-4">
          {[1, 2].map(i => <div key={i} className="col-span-6 h-72 bg-gray-800 rounded-xl" />)}
        </div>
      </div>
    )
  }

  if (!dashboard) {
    return <div className="p-6 text-red-400">Tableau de bord introuvable.</div>
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('/dashboards')} className="btn-ghost p-1.5 rounded-lg">
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-lg font-semibold text-gray-100 truncate">{dashboard.name}</h1>
          {dashboard.description && <p className="text-sm text-gray-500">{dashboard.description}</p>}
        </div>
        <button
          onClick={refresh}
          disabled={isRefreshing}
          className="btn-ghost flex items-center gap-2 px-3 py-2"
        >
          <RefreshCw size={15} className={isRefreshing ? 'animate-spin' : ''} />
          Rafraîchir
        </button>
        <button
          onClick={() => navigate(`/dashboards/${dashboard.id}/edit`)}
          className="btn-primary flex items-center gap-2 px-3 py-2"
        >
          <Edit2 size={15} />
          Éditer
        </button>
      </div>

      {/* Grid */}
      <DashboardGrid
        widgets={dashboard.widgets}
        widgetResults={widgetResults}
        widgetLoading={widgetLoading}
        isEditing={false}
      />
    </div>
  )
}
