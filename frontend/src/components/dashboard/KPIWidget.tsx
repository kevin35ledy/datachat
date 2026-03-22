import type { QueryResult, WidgetConfig } from '../../api/types'

interface Props {
  result: QueryResult
  config: WidgetConfig
}

export function KPIWidget({ result, config }: Props) {
  if (result.total_count === 0 || result.columns.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 text-2xl font-bold">
        —
      </div>
    )
  }

  const col = config.y_columns[0]
    ?? result.columns.find(c => c.type_category === 'numeric')?.name
    ?? result.columns[0].name

  const raw = result.rows[0]?.[col]
  const value = typeof raw === 'number'
    ? raw.toLocaleString()
    : raw != null ? String(raw) : '—'

  const label = config.title || col

  return (
    <div className="flex flex-col items-center justify-center h-full gap-2">
      <span className="text-5xl font-bold text-brand-400 tabular-nums">{value}</span>
      <span className="text-sm text-gray-500 uppercase tracking-wider">{label}</span>
    </div>
  )
}
