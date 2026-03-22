// Mirror of backend Pydantic models

export type DBType = 'postgresql' | 'mysql' | 'sqlite' | 'csv' | 'mongodb' | 'bigquery'

export interface ConnectionConfig {
  id: string
  name: string
  db_type: DBType
  url: string
  schema_name: string
  ssl: boolean
  created_at: string
  updated_at: string
}

export interface ConnectionCreate {
  name: string
  db_type: DBType
  url: string
  schema_name?: string
  ssl?: boolean
}

export interface ConnectionStatus {
  conn_id: string
  healthy: boolean
  latency_ms: number | null
  error: string | null
  checked_at: string
}

export interface ColumnMeta {
  name: string
  type_name: string
  type_category: 'text' | 'numeric' | 'date' | 'boolean' | 'json' | 'unknown'
  nullable: boolean
}

export interface QueryResult {
  query_id: string
  columns: ColumnMeta[]
  rows: Record<string, unknown>[]
  total_count: number
  truncated: boolean
  execution_time_ms: number
}

export interface ChartSuggestion {
  type: 'bar' | 'line' | 'scatter' | 'pie' | 'bar_grouped' | 'area'
  x_column: string
  y_column: string
  y_columns: string[]
}

export interface SQLQuery {
  raw_sql: string
  validated_sql: string
  dialect: string
  is_safe: boolean
  explanation: string
  confidence: number
  validation_warnings: string[]
}

export interface ChatResponse {
  message_id: string
  session_id: string
  nl_query: string
  sql_query: SQLQuery | null
  result: QueryResult | null
  chart_suggestion: ChartSuggestion | null
  summary: string
  error: string | null
  created_at: string
}

export interface QueryHistoryEntry {
  id: string
  connection_id: string
  session_id: string
  nl_text: string
  sql_text: string
  row_count: number
  execution_time_ms: number
  created_at: string
}

export interface SchemaColumn {
  name: string
  type_name: string
  nullable: boolean
  is_primary_key: boolean
  is_foreign_key: boolean
}

export interface SchemaTable {
  name: string
  schema_name: string
  columns: SchemaColumn[]
  row_count: number | null
}

export interface SchemaInfo {
  database_name: string
  dialect: string
  tables: SchemaTable[]
}

// --- Dashboard types ---

export type WidgetType = 'chart' | 'table' | 'kpi' | 'text'
export type ChartType = 'bar' | 'line' | 'scatter' | 'pie' | 'bar_grouped' | 'area'

export interface WidgetConfig {
  chart_type: ChartType | null
  x_column: string | null
  y_columns: string[]
  color: string | null
  title: string
}

export interface DashboardWidget {
  id: string
  widget_type: WidgetType
  title: string
  nl_query: string
  sql_query: string
  config: WidgetConfig
  position: number
  width: 1 | 2 | 3
  height: 1 | 2
  created_at: string
}

export interface Dashboard {
  id: string
  name: string
  description: string
  connection_id: string
  widgets: DashboardWidget[]
  created_at: string
  updated_at: string
}

export interface DashboardCreate {
  name: string
  description?: string
  connection_id: string
}

export interface DashboardUpdate {
  name?: string
  description?: string
  widgets?: DashboardWidget[]
}

export interface AddWidgetRequest {
  nl_text: string
  widget_type?: WidgetType
}

export interface WidgetRefreshResult {
  widget_id: string
  result: QueryResult | null
  error: string | null
}

export interface DashboardRefreshResult {
  dashboard_id: string
  results: WidgetRefreshResult[]
}
