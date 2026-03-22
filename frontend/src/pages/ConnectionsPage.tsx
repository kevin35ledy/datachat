import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { connectionsApi } from '../api/connections'
import { useConnectionStore } from '../stores/connectionStore'
import type { ConnectionCreate } from '../api/types'
import { Plus, Trash2, Zap, CheckCircle, XCircle, Loader } from 'lucide-react'
import clsx from 'clsx'

export function ConnectionsPage() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const { setConnections, addConnection, removeConnection, setActiveConnection, activeConnectionId } =
    useConnectionStore()

  const { data: connections = [], isLoading } = useQuery({
    queryKey: ['connections'],
    queryFn: async () => {
      const data = await connectionsApi.list()
      setConnections(data)
      return data
    },
  })

  const createMutation = useMutation({
    mutationFn: connectionsApi.create,
    onSuccess: (conn) => {
      addConnection(conn)
      queryClient.invalidateQueries({ queryKey: ['connections'] })
      setShowForm(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: connectionsApi.delete,
    onSuccess: (_, id) => {
      removeConnection(id)
      queryClient.invalidateQueries({ queryKey: ['connections'] })
    },
  })

  return (
    <div className="p-6 max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-100">Connexions</h1>
          <p className="text-sm text-gray-500 mt-1">Gérez vos sources de données</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary flex items-center gap-2">
          <Plus size={16} />
          Nouvelle connexion
        </button>
      </div>

      {/* Add form */}
      {showForm && (
        <ConnectionForm
          onSubmit={(data) => createMutation.mutate(data)}
          onCancel={() => setShowForm(false)}
          isLoading={createMutation.isPending}
        />
      )}

      {/* Connection list */}
      {isLoading ? (
        <div className="flex items-center gap-2 text-gray-500">
          <Loader size={16} className="animate-spin" />
          <span>Chargement...</span>
        </div>
      ) : connections.length === 0 ? (
        <div className="card text-center py-12 text-gray-500">
          <p className="text-sm">Aucune connexion configurée.</p>
          <p className="text-xs mt-1">Cliquez sur &quot;Nouvelle connexion&quot; pour commencer.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {connections.map((conn) => (
            <div
              key={conn.id}
              className={clsx(
                'card flex items-center gap-4 cursor-pointer transition-all',
                activeConnectionId === conn.id ? 'ring-2 ring-brand-500' : 'hover:border-gray-700'
              )}
              onClick={() => setActiveConnection(conn.id)}
            >
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-200">{conn.name}</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {conn.db_type} · {conn.url.split('@').pop()?.split('/')[0] ?? conn.url.substring(0, 40)}
                </p>
              </div>
              {activeConnectionId === conn.id && (
                <span className="text-xs text-brand-400 flex items-center gap-1">
                  <CheckCircle size={12} /> Active
                </span>
              )}
              <TestButton connId={conn.id} />
              <button
                onClick={(e) => { e.stopPropagation(); deleteMutation.mutate(conn.id) }}
                className="text-gray-600 hover:text-red-400 transition-colors"
                title="Supprimer"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function TestButton({ connId }: { connId: string }) {
  const [status, setStatus] = useState<'idle' | 'testing' | 'ok' | 'error'>('idle')

  const handleTest = async (e: React.MouseEvent) => {
    e.stopPropagation()
    setStatus('testing')
    try {
      const result = await connectionsApi.test(connId)
      setStatus(result.healthy ? 'ok' : 'error')
      setTimeout(() => setStatus('idle'), 3000)
    } catch {
      setStatus('error')
      setTimeout(() => setStatus('idle'), 3000)
    }
  }

  return (
    <button onClick={handleTest} className="text-gray-500 hover:text-gray-300 transition-colors" title="Tester la connexion">
      {status === 'testing' && <Loader size={14} className="animate-spin" />}
      {status === 'ok' && <CheckCircle size={14} className="text-green-400" />}
      {status === 'error' && <XCircle size={14} className="text-red-400" />}
      {status === 'idle' && <Zap size={14} />}
    </button>
  )
}

function ConnectionForm({
  onSubmit,
  onCancel,
  isLoading,
}: {
  onSubmit: (data: ConnectionCreate) => void
  onCancel: () => void
  isLoading: boolean
}) {
  const [form, setForm] = useState<ConnectionCreate>({
    name: '',
    db_type: 'postgresql',
    url: '',
    schema_name: 'public',
    ssl: false,
  })

  const placeholders: Record<string, string> = {
    postgresql: 'postgresql://user:password@localhost:5432/mydb',
    mysql: 'mysql://user:password@localhost:3306/mydb',
    sqlite: 'sqlite:///path/to/database.db',
    csv: 'csv:///path/to/directory',
    mongodb: 'mongodb://user:password@localhost:27017/mydb',
    bigquery: 'bigquery://project-id/dataset',
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (form.name && form.url) onSubmit(form)
  }

  return (
    <form onSubmit={handleSubmit} className="card mb-6 space-y-4">
      <h2 className="text-sm font-semibold text-gray-200">Nouvelle connexion</h2>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Nom</label>
          <input
            className="input-field"
            placeholder="Ma base de données"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
          />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Type</label>
          <select
            className="input-field"
            value={form.db_type}
            onChange={(e) => setForm({ ...form, db_type: e.target.value as ConnectionCreate['db_type'] })}
          >
            <option value="postgresql">PostgreSQL</option>
            <option value="mysql">MySQL / MariaDB</option>
            <option value="sqlite">SQLite</option>
            <option value="csv">CSV (fichiers)</option>
          </select>
        </div>
      </div>

      <div>
        <label className="block text-xs text-gray-400 mb-1">URL de connexion</label>
        <input
          className="input-field font-mono text-xs"
          placeholder={placeholders[form.db_type]}
          value={form.url}
          onChange={(e) => setForm({ ...form, url: e.target.value })}
          required
        />
      </div>

      <div className="flex gap-2 justify-end">
        <button type="button" onClick={onCancel} className="btn-ghost">
          Annuler
        </button>
        <button type="submit" disabled={isLoading} className="btn-primary">
          {isLoading ? 'Création...' : 'Créer'}
        </button>
      </div>
    </form>
  )
}
