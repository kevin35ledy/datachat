import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { connectionsApi } from '../api/connections'
import type { SchemaAnnotations, TableAnnotation, ColumnAnnotation } from '../api/types'
import { ArrowLeft, Save, ChevronDown, ChevronRight } from 'lucide-react'

export function ConnectionAnnotationsPage() {
  const { connId } = useParams<{ connId: string }>()
  const navigate = useNavigate()
  const [annotations, setAnnotations] = useState<SchemaAnnotations | null>(null)
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set())

  const { data: schema, isLoading: schemaLoading } = useQuery({
    queryKey: ['connection-schema', connId],
    queryFn: () => connectionsApi.getSchema(connId!),
    enabled: !!connId,
  })

  const { data: existingAnnotations, isLoading: annotationsLoading } = useQuery({
    queryKey: ['connection-annotations', connId],
    queryFn: () => connectionsApi.getAnnotations(connId!),
    enabled: !!connId,
  })

  useEffect(() => {
    if (existingAnnotations) setAnnotations(existingAnnotations)
  }, [existingAnnotations])

  const saveMutation = useMutation({
    mutationFn: (data: SchemaAnnotations) => connectionsApi.saveAnnotations(connId!, data),
    onSuccess: () => navigate('/connections'),
  })

  const getTableAnnotation = (tableName: string): TableAnnotation => {
    return annotations?.tables[tableName] ?? { description: '', columns: {} }
  }

  const getColAnnotation = (tableName: string, colName: string): ColumnAnnotation => {
    return getTableAnnotation(tableName).columns[colName] ?? { description: '', possible_values: [] }
  }

  const updateTableDesc = (tableName: string, description: string) => {
    setAnnotations(prev => {
      const tables = { ...(prev?.tables ?? {}) }
      tables[tableName] = { ...getTableAnnotation(tableName), description }
      return { conn_id: connId!, tables, updated_at: new Date().toISOString() }
    })
  }

  const updateColDesc = (tableName: string, colName: string, description: string) => {
    setAnnotations(prev => {
      const tables = { ...(prev?.tables ?? {}) }
      const ta = { ...getTableAnnotation(tableName) }
      ta.columns = { ...ta.columns, [colName]: { ...getColAnnotation(tableName, colName), description } }
      tables[tableName] = ta
      return { conn_id: connId!, tables, updated_at: new Date().toISOString() }
    })
  }

  const updateColValues = (tableName: string, colName: string, raw: string) => {
    const possible_values = raw.split(',').map(v => v.trim()).filter(Boolean)
    setAnnotations(prev => {
      const tables = { ...(prev?.tables ?? {}) }
      const ta = { ...getTableAnnotation(tableName) }
      ta.columns = { ...ta.columns, [colName]: { ...getColAnnotation(tableName, colName), possible_values } }
      tables[tableName] = ta
      return { conn_id: connId!, tables, updated_at: new Date().toISOString() }
    })
  }

  const toggleTable = (tableName: string) => {
    setExpandedTables(prev => {
      const next = new Set(prev)
      if (next.has(tableName)) next.delete(tableName)
      else next.add(tableName)
      return next
    })
  }

  const handleSave = () => {
    saveMutation.mutate(annotations ?? { conn_id: connId!, tables: {}, updated_at: new Date().toISOString() })
  }

  if (schemaLoading || annotationsLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-400">Chargement du schéma...</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800 shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/connections')} className="btn-ghost p-2">
            <ArrowLeft size={16} />
          </button>
          <div>
            <h1 className="text-base font-semibold text-gray-100">Annotations du schéma</h1>
            <p className="text-xs text-gray-500 mt-0.5">Décrivez vos tables et colonnes pour améliorer la précision des requêtes</p>
          </div>
        </div>
        <button
          onClick={handleSave}
          disabled={saveMutation.isPending}
          className="btn-primary flex items-center gap-2"
        >
          <Save size={14} />
          {saveMutation.isPending ? 'Enregistrement...' : 'Enregistrer'}
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-3">
        {schema?.tables.map(table => {
          const isExpanded = expandedTables.has(table.name)
          const ta = getTableAnnotation(table.name)

          return (
            <div key={table.name} className="card">
              {/* Table header */}
              <div className="flex items-start gap-3">
                <button
                  onClick={() => toggleTable(table.name)}
                  className="mt-1 text-gray-500 hover:text-gray-300 transition-colors"
                >
                  {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </button>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-mono text-sm font-medium text-brand-400">{table.name}</span>
                    {table.row_count != null && (
                      <span className="text-xs text-gray-500">~{table.row_count.toLocaleString()} lignes</span>
                    )}
                  </div>
                  <input
                    type="text"
                    value={ta.description}
                    onChange={e => updateTableDesc(table.name, e.target.value)}
                    placeholder="Description métier de cette table..."
                    className="input-field text-xs"
                  />
                </div>
              </div>

              {/* Columns */}
              {isExpanded && (
                <div className="mt-4 ml-7 space-y-3">
                  {table.columns.map(col => {
                    const ca = getColAnnotation(table.name, col.name)
                    return (
                      <div key={col.name} className="bg-gray-800/50 rounded-lg p-3 space-y-2">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs text-gray-300">{col.name}</span>
                          <span className="text-xs text-gray-600">{col.type_name}</span>
                          {col.is_primary_key && <span className="text-xs text-brand-500">PK</span>}
                          {col.is_foreign_key && <span className="text-xs text-gray-500">FK</span>}
                        </div>
                        <input
                          type="text"
                          value={ca.description}
                          onChange={e => updateColDesc(table.name, col.name, e.target.value)}
                          placeholder="Description de la colonne..."
                          className="input-field text-xs"
                        />
                        <input
                          type="text"
                          value={ca.possible_values.join(', ')}
                          onChange={e => updateColValues(table.name, col.name, e.target.value)}
                          placeholder="Valeurs possibles (séparées par des virgules)..."
                          className="input-field text-xs"
                        />
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
