import type { QueryResult, WidgetConfig, WidgetType, ChartType, PivotAggregation } from '../../api/types'
import clsx from 'clsx'

interface Props {
  widgetType: WidgetType
  result: QueryResult | undefined
  config: WidgetConfig
  onChange: (config: WidgetConfig) => void
}

const CHART_TYPES: { type: ChartType; label: string }[] = [
  { type: 'bar', label: 'Barres' },
  { type: 'line', label: 'Ligne' },
  { type: 'area', label: 'Aire' },
  { type: 'pie', label: 'Camembert' },
  { type: 'scatter', label: 'Nuage' },
  { type: 'bar_grouped', label: 'Barres groupées' },
]

const AGG_OPTIONS = [
  { value: 'sum', label: 'Somme' },
  { value: 'count', label: 'Nombre' },
  { value: 'avg', label: 'Moyenne' },
  { value: 'min', label: 'Min' },
  { value: 'max', label: 'Max' },
]

export function WidgetConfigPanel({ widgetType, result, config, onChange }: Props) {
  const columns = result?.columns ?? []
  const numericCols = columns.filter(c =>
    c.type_category === 'numeric' || (result?.rows[0] && typeof result.rows[0][c.name] === 'number')
  )
  const allCols = columns.map(c => c.name)

  if (widgetType === 'chart') {
    return (
      <div className="bg-gray-800/60 rounded-lg p-3 space-y-3 text-xs">
        {/* Chart type */}
        <div>
          <p className="text-gray-500 mb-1.5 uppercase tracking-wide text-[10px]">Type</p>
          <div className="flex flex-wrap gap-1">
            {CHART_TYPES.map(({ type, label }) => (
              <button
                key={type}
                onClick={() => onChange({ ...config, chart_type: type })}
                className={clsx(
                  'px-2 py-1 rounded text-xs transition-colors',
                  config.chart_type === type
                    ? 'bg-brand-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                )}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* X axis */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <p className="text-gray-500 mb-1 uppercase tracking-wide text-[10px]">Axe X</p>
            <select
              value={config.x_column ?? ''}
              onChange={e => onChange({ ...config, x_column: e.target.value || null })}
              className="input-field text-xs py-1"
            >
              <option value="">Auto</option>
              {allCols.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          {/* Y columns */}
          <div>
            <p className="text-gray-500 mb-1 uppercase tracking-wide text-[10px]">Axe Y</p>
            <div className="space-y-0.5 max-h-24 overflow-y-auto">
              {allCols.map(c => (
                <label key={c} className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.y_columns.includes(c)}
                    onChange={e => {
                      const next = e.target.checked
                        ? [...config.y_columns, c]
                        : config.y_columns.filter(x => x !== c)
                      onChange({ ...config, y_columns: next })
                    }}
                    className="accent-brand-500"
                  />
                  <span className="text-gray-300 font-mono">{c}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (widgetType === 'pivot') {
    if (!allCols.length) {
      return (
        <div className="bg-gray-800/60 rounded-lg p-3 text-xs text-gray-500 text-center">
          Chargement des données en cours…
        </div>
      )
    }

    const rowCols = config.pivot_row_cols ?? []
    const colCols = config.pivot_col_cols ?? []
    const aggs: PivotAggregation[] = config.pivot_aggregations ?? []

    const toggleDim = (field: 'pivot_row_cols' | 'pivot_col_cols', col: string, checked: boolean) => {
      const current = (config[field] ?? []) as string[]
      const next = checked ? [...current, col] : current.filter(x => x !== col)
      onChange({ ...config, [field]: next })
    }

    const updateAgg = (i: number, patch: Partial<PivotAggregation>) => {
      const next = aggs.map((a, idx) => idx === i ? { ...a, ...patch } : a)
      onChange({ ...config, pivot_aggregations: next })
    }

    const removeAgg = (i: number) => {
      onChange({ ...config, pivot_aggregations: aggs.filter((_, idx) => idx !== i) })
    }

    const addAgg = () => {
      onChange({ ...config, pivot_aggregations: [...aggs, { field: allCols[0], agg: 'sum', label: '' }] })
    }

    const labelCls = 'text-gray-500 uppercase tracking-wide text-[10px] mb-1'

    return (
      <div className="bg-gray-800/60 rounded-lg p-3 space-y-3 text-xs">
        {/* Lignes + Colonnes */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className={labelCls}>Lignes</p>
            <div className="space-y-0.5 max-h-20 overflow-y-auto">
              {allCols.map(c => (
                <label key={c} className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={rowCols.includes(c)}
                    onChange={e => toggleDim('pivot_row_cols', c, e.target.checked)}
                    className="accent-brand-500"
                  />
                  <span className="text-gray-300 font-mono">{c}</span>
                </label>
              ))}
            </div>
          </div>
          <div>
            <p className={labelCls}>Colonnes</p>
            <div className="space-y-0.5 max-h-20 overflow-y-auto">
              {allCols.map(c => (
                <label key={c} className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={colCols.includes(c)}
                    onChange={e => toggleDim('pivot_col_cols', c, e.target.checked)}
                    className="accent-brand-500"
                  />
                  <span className="text-gray-300 font-mono">{c}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* Agrégations */}
        <div>
          <p className={labelCls}>Agrégations</p>
          <div className="space-y-1">
            {aggs.map((a, i) => (
              <div key={i} className="flex items-center gap-1.5">
                <select
                  value={a.field}
                  onChange={e => updateAgg(i, { field: e.target.value })}
                  className="input-field text-xs py-0.5 flex-1 min-w-0"
                >
                  {allCols.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
                <select
                  value={a.agg}
                  onChange={e => updateAgg(i, { agg: e.target.value })}
                  className="input-field text-xs py-0.5 w-24 shrink-0"
                >
                  {AGG_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                <button
                  onClick={() => removeAgg(i)}
                  className="text-gray-600 hover:text-red-400 shrink-0 px-1"
                  title="Supprimer"
                >
                  ✕
                </button>
              </div>
            ))}
            <button
              onClick={addAgg}
              className="text-brand-400 hover:text-brand-300 text-[11px] mt-0.5"
            >
              + Ajouter une agrégation
            </button>
          </div>
        </div>
      </div>
    )
  }

  return null
}
