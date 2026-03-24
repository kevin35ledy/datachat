import {
  ResponsiveContainer,
  BarChart, Bar,
  LineChart, Line,
  AreaChart, Area,
  ScatterChart, Scatter, XAxis as ScatterX, YAxis as ScatterY,
  PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from 'recharts'
import type { QueryResult, WidgetConfig } from '../../api/types'

const COLORS = ['#06b6d4', '#0ea5e9', '#6366f1', '#a855f7', '#ec4899', '#f59e0b']

const AXIS_STYLE = { fill: '#9ca3af', fontSize: 11 }
const GRID_STYLE = { strokeDasharray: '3 3', stroke: '#374151' }
const TOOLTIP_STYLE = {
  contentStyle: { backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 8 },
  labelStyle: { color: '#e5e7eb' },
  itemStyle: { color: '#9ca3af' },
}

function fmt(v: unknown) {
  const n = Number(v)
  return isNaN(n) ? String(v) : n.toLocaleString()
}

interface Props {
  result: QueryResult
  config: WidgetConfig
}

export function ChartWidget({ result, config }: Props) {
  const data = result.rows as Record<string, unknown>[]

  // Auto-detect chart config from result shape when backend didn't suggest one
  const chartType = config.chart_type ?? 'bar'

  // isNumericValue: true for JS numbers and numeric strings (handles all DB serializations)
  const isNumericValue = (v: unknown): boolean =>
    typeof v === 'number' || (typeof v === 'string' && v !== '' && !isNaN(Number(v)))

  // xKey: prefer config, then first non-numeric column, then first column
  const xKey = config.x_column
    ?? result.columns.find(c => c.type_category === 'text' || c.type_category === 'date' || c.type_category === 'unknown')?.name
    ?? result.columns.find(c => !isNumericValue(data[0]?.[c.name]))?.name
    ?? result.columns[0]?.name
    ?? ''

  // yKeys: prefer config, then any column (except xKey) whose first value looks numeric
  const yKeys = config.y_columns.length > 0
    ? config.y_columns
    : result.columns
        .filter(c => c.name !== xKey && (
          c.type_category === 'numeric' ||
          isNumericValue(data[0]?.[c.name])
        ))
        .map(c => c.name)

  if (data.length === 0) {
    return <div className="flex items-center justify-center h-full text-gray-500 text-sm">Aucune donnée</div>
  }

  if (yKeys.length === 0) {
    return <div className="flex items-center justify-center h-full text-gray-500 text-sm">Aucune colonne numérique détectée</div>
  }

  const common = (
    <>
      <CartesianGrid {...GRID_STYLE} />
      <XAxis dataKey={xKey} tick={AXIS_STYLE} />
      <YAxis tick={AXIS_STYLE} tickFormatter={fmt} width={60} />
      <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [fmt(v), '']} />
      <Legend wrapperStyle={{ fontSize: 11, color: '#9ca3af' }} />
    </>
  )

  return (
    <ResponsiveContainer width="100%" height="100%">
      {chartType === 'pie' ? (
        <PieChart>
          <Pie
            data={data}
            dataKey={yKeys[0] ?? 'value'}
            nameKey={xKey}
            cx="50%"
            cy="50%"
            outerRadius="70%"
            label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
            labelLine={{ stroke: '#6b7280' }}
          >
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [fmt(v), '']} />
          <Legend wrapperStyle={{ fontSize: 11, color: '#9ca3af' }} />
        </PieChart>
      ) : chartType === 'scatter' ? (
        <ScatterChart>
          <CartesianGrid {...GRID_STYLE} />
          <ScatterX dataKey={xKey} tick={AXIS_STYLE} />
          <ScatterY dataKey={yKeys[0]} tick={AXIS_STYLE} tickFormatter={fmt} />
          <Tooltip {...TOOLTIP_STYLE} />
          <Scatter data={data} fill={COLORS[0]} />
        </ScatterChart>
      ) : chartType === 'line' ? (
        <LineChart data={data}>
          {common}
          {yKeys.map((k, i) => (
            <Line key={k} type="monotone" dataKey={k} stroke={COLORS[i % COLORS.length]} dot={false} strokeWidth={2} />
          ))}
        </LineChart>
      ) : chartType === 'area' ? (
        <AreaChart data={data}>
          {common}
          {yKeys.map((k, i) => (
            <Area key={k} type="monotone" dataKey={k} stroke={COLORS[i % COLORS.length]} fill={COLORS[i % COLORS.length] + '33'} strokeWidth={2} />
          ))}
        </AreaChart>
      ) : (
        // bar + bar_grouped
        <BarChart data={data}>
          {common}
          {yKeys.map((k, i) => (
            <Bar key={k} dataKey={k} fill={COLORS[i % COLORS.length]} radius={[3, 3, 0, 0]} />
          ))}
        </BarChart>
      )}
    </ResponsiveContainer>
  )
}
