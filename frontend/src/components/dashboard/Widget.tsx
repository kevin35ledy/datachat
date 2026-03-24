import { useState, useEffect, useRef } from 'react'
import { ChevronUp, ChevronDown, Trash2, Maximize2, Minimize2, AlertTriangle, Pencil, RefreshCw, X, SlidersHorizontal } from 'lucide-react'
import type { DashboardWidget, QueryResult, WidgetConfig } from '../../api/types'
import { ChartWidget } from './ChartWidget'
import { TableWidget } from './TableWidget'
import { KPIWidget } from './KPIWidget'
import { PivotWidget } from './PivotWidget'
import { WidgetConfigPanel } from './WidgetConfigPanel'

interface Props {
  widget: DashboardWidget
  result?: QueryResult
  error?: string
  isLoading?: boolean
  isEditing?: boolean
  isRegenerating?: boolean
  onDelete?: (id: string) => void
  onMoveUp?: (id: string) => void
  onMoveDown?: (id: string) => void
  onResizeWidth?: (id: string, width: 1 | 2 | 3) => void
  onRegenerate?: (id: string, nlText: string) => void
  onConfigChange?: (id: string, config: WidgetConfig) => void
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

export function Widget({ widget, result, error, isLoading, isEditing, isRegenerating, onDelete, onMoveUp, onMoveDown, onResizeWidth, onRegenerate, onConfigChange }: Props) {
  const [editOpen, setEditOpen] = useState(false)
  const [configOpen, setConfigOpen] = useState(false)
  const [editText, setEditText] = useState(widget.nl_query)
  const [configDraft, setConfigDraft] = useState<WidgetConfig>(widget.config)
  const configSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    setConfigDraft(widget.config)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [widget.id])

  const handleConfigChange = (cfg: WidgetConfig) => {
    setConfigDraft(cfg)
    if (configSaveTimer.current) clearTimeout(configSaveTimer.current)
    configSaveTimer.current = setTimeout(() => {
      onConfigChange?.(widget.id, cfg)
    }, 300)
  }

  const handleRegenerate = () => {
    if (editText.trim()) {
      onRegenerate?.(widget.id, editText.trim())
      setEditOpen(false)
    }
  }

  const showConfigBtn = widget.widget_type === 'chart' || widget.widget_type === 'pivot'

  return (
    <div className={`card flex flex-col gap-2 ${HEIGHT_CLASS[widget.height]}`}>
      {/* Header */}
      <div className="flex items-center justify-between gap-2 shrink-0">
        <span className="text-sm font-medium text-gray-200 truncate">{widget.title}</span>
        {widget.config.inferred && (
          <span title="Types de colonnes déduits automatiquement — le graphique peut être inexact" className="shrink-0 text-amber-500">
            <AlertTriangle size={13} />
          </span>
        )}
        <div className="flex items-center gap-1 shrink-0">
          {showConfigBtn && (
            <button
              onClick={() => { setConfigOpen(v => !v); setEditOpen(false) }}
              className={`p-1 rounded transition-colors ${configOpen ? 'text-brand-400' : 'text-gray-500 hover:text-brand-400'}`}
              title="Configurer le widget"
            >
              <SlidersHorizontal size={13} />
            </button>
          )}
          <button
            onClick={() => { setEditText(widget.nl_query); setEditOpen(v => !v); setConfigOpen(false) }}
            className="p-1 text-gray-500 hover:text-brand-400 rounded"
            title="Modifier le prompt"
          >
            <Pencil size={13} />
          </button>
          {isEditing && (
            <>
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
            </>
          )}
        </div>
      </div>

      {/* NL query display */}
      {!editOpen && !configOpen && (
        <p className="text-xs text-gray-600 truncate shrink-0" title={widget.nl_query}>{widget.nl_query}</p>
      )}

      {/* Config panel */}
      {configOpen && (
        <div className="shrink-0">
          <WidgetConfigPanel
            widgetType={widget.widget_type}
            result={result}
            config={configDraft}
            onChange={handleConfigChange}
          />
        </div>
      )}

      {/* Inline edit */}
      {editOpen && (
        <div className="shrink-0 space-y-1.5">
          <textarea
            value={editText}
            onChange={e => setEditText(e.target.value)}
            rows={2}
            className="input-field text-xs resize-none"
            placeholder="Décrivez votre widget..."
          />
          <div className="flex gap-2">
            <button
              onClick={handleRegenerate}
              disabled={isRegenerating || !editText.trim()}
              className="btn-primary text-xs py-1 flex items-center gap-1"
            >
              <RefreshCw size={11} className={isRegenerating ? 'animate-spin' : ''} />
              {isRegenerating ? 'Régénération...' : 'Régénérer'}
            </button>
            <button onClick={() => setEditOpen(false)} className="btn-ghost text-xs py-1 flex items-center gap-1">
              <X size={11} />
              Annuler
            </button>
          </div>
        </div>
      )}

      {/* Body */}
      <div className="flex-1 min-h-0">
        {configOpen ? (
          <div className="flex items-center justify-center h-full text-gray-600 text-xs">
            Fermez le panneau ⚙ pour voir l'aperçu
          </div>
        ) : isLoading || isRegenerating ? (
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
          <ChartWidget result={result} config={configDraft} />
        ) : widget.widget_type === 'table' ? (
          <TableWidget result={result} />
        ) : widget.widget_type === 'kpi' ? (
          <KPIWidget result={result} config={widget.config} />
        ) : widget.widget_type === 'pivot' ? (
          <PivotWidget result={result} config={configDraft} />
        ) : (
          <p className="text-sm text-gray-400 p-2">{widget.nl_query}</p>
        )}
      </div>
    </div>
  )
}
