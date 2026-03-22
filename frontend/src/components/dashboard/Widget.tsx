import { ChevronUp, ChevronDown, Trash2, Maximize2, Minimize2 } from 'lucide-react'
import type { DashboardWidget, QueryResult } from '../../api/types'
import { ChartWidget } from './ChartWidget'
import { TableWidget } from './TableWidget'
import { KPIWidget } from './KPIWidget'

interface Props {
  widget: DashboardWidget
  result?: QueryResult
  error?: string
  isLoading?: boolean
  isEditing?: boolean
  onDelete?: (id: string) => void
  onMoveUp?: (id: string) => void
  onMoveDown?: (id: string) => void
  onResizeWidth?: (id: string, width: 1 | 2 | 3) => void
}

const HEIGHT_CLASS: Record<1 | 2, string> = {
  1: 'h-72',
  2: 'h-[36rem]',
}

function Skeleton() {
  return (
    <div className="h-full flex flex-col gap-3 p-2 animate-pulse">
      <div className="h-4 bg-gray-800 rounded w-2/3" />
      <div className="flex-1 bg-gray-800 rounded" />
    </div>
  )
}

export function Widget({ widget, result, error, isLoading, isEditing, onDelete, onMoveUp, onMoveDown, onResizeWidth }: Props) {
  return (
    <div className={`card flex flex-col gap-2 ${HEIGHT_CLASS[widget.height]}`}>
      {/* Header */}
      <div className="flex items-center justify-between gap-2 shrink-0">
        <span className="text-sm font-medium text-gray-200 truncate">{widget.title}</span>
        {isEditing && (
          <div className="flex items-center gap-1 shrink-0">
            <button onClick={() => onMoveUp?.(widget.id)} className="p-1 text-gray-500 hover:text-gray-300 rounded" title="Monter">
              <ChevronUp size={14} />
            </button>
            <button onClick={() => onMoveDown?.(widget.id)} className="p-1 text-gray-500 hover:text-gray-300 rounded" title="Descendre">
              <ChevronDown size={14} />
            </button>
            <button
              onClick={() => onResizeWidth?.(widget.id, widget.width === 3 ? 2 : widget.width === 2 ? 1 : 3)}
              className="p-1 text-gray-500 hover:text-gray-300 rounded"
              title={widget.width === 3 ? 'Réduire' : 'Agrandir'}
            >
              {widget.width === 3 ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </button>
            <button onClick={() => onDelete?.(widget.id)} className="p-1 text-red-500 hover:text-red-400 rounded" title="Supprimer">
              <Trash2 size={14} />
            </button>
          </div>
        )}
      </div>

      {/* Body */}
      <div className="flex-1 min-h-0">
        {isLoading ? (
          <Skeleton />
        ) : error ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-red-400 text-sm text-center px-4">{error}</p>
          </div>
        ) : !result ? (
          <div className="flex items-center justify-center h-full text-gray-600 text-sm">
            Aucune donnée
          </div>
        ) : widget.widget_type === 'chart' ? (
          <ChartWidget result={result} config={widget.config} />
        ) : widget.widget_type === 'table' ? (
          <TableWidget result={result} />
        ) : widget.widget_type === 'kpi' ? (
          <KPIWidget result={result} config={widget.config} />
        ) : (
          <p className="text-sm text-gray-400 p-2">{widget.nl_query}</p>
        )}
      </div>
    </div>
  )
}
