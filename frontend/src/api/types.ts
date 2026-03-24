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
  inferred?: boolean
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
  comment: string
  possible_values: string[]
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

export interface PivotAggregation {
  field: string
  agg: string       // sum|count|avg|min|max
  label?: string    // custom label; auto-generated if empty
}

export type WidgetType = 'chart' | 'table' | 'kpi' | 'text' | 'pivot'
export type ChartType = 'bar' | 'line' | 'scatter' | 'pie' | 'bar_grouped' | 'area'

export interface WidgetConfig {
  chart_type: ChartType | null
  x_column: string | null
  y_columns: string[]
  color: string | null
  title: string
  inferred?: boolean
  // Pivot config
  pivot_row_cols?: string[]
  pivot_col_cols?: string[]
  pivot_aggregations?: PivotAggregation[]
  // deprecated — kept for backward-compat migration
  pivot_value_cols?: string[]
  pivot_agg?: string
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

export interface AddWidgetResponse {
  dashboard: Dashboard
  warnings: string[]
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

export interface RegenerateWidgetRequest {
  nl_text: string
}

// --- Annotation types ---

export interface ColumnAnnotation {
  description: string
  possible_values: string[]
}

export interface TableAnnotation {
  description: string
  columns: Record<string, ColumnAnnotation>
}

export interface SchemaAnnotations {
  conn_id: string
  tables: Record<string, TableAnnotation>
  updated_at: string
}

// --- Clarification types ---

export interface ClarificationQuestion {
  id: string
  question: string
  context: string
  suggestions: string[]
}

export interface ClarificationResponse {
  questions: ClarificationQuestion[]
}
