import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { LayoutDashboard, Plus, ExternalLink, Edit2, Trash2, Database } from 'lucide-react'
import { dashboardsApi } from '../api/dashboards'
import { useConnectionStore } from '../stores/connectionStore'
import type { DashboardCreate } from '../api/types'

export function DashboardsPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { connections } = useConnectionStore()

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<DashboardCreate>({ name: '', description: '', connection_id: '' })

  const { data: dashboards = [], isLoading } = useQuery({
    queryKey: ['dashboards'],
    queryFn: () => dashboardsApi.list(),
  })

  const createMut = useMutation({
    mutationFn: (data: DashboardCreate) => dashboardsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['dashboards'] })
      setShowForm(false)
      setForm({ name: '', description: '', connection_id: '' })
    },
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => dashboardsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dashboards'] }),
  })

  const handleCreate = () => {
    if (!form.name.trim() || !form.connection_id) return
    createMut.mutate(form)
  }

  const connName = (connId: string) =>
    connections.find(c => c.id === connId)?.name ?? connId

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <LayoutDashboard size={22} className="text-brand-500" />
          <h1 className="text-lg font-semibold text-gray-100">Tableaux de bord</h1>
        </div>
        <button onClick={() => setShowForm(v => !v)} className="btn-primary flex items-center gap-2 px-4 py-2">
          <Plus size={16} />
          Nouveau
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="card flex flex-col gap-4 max-w-lg">
          <p className="text-sm font-medium text-gray-300">Nouveau tableau de bord</p>
          <input
            className="input-field"
            placeholder="Nom *"
            value={form.name}
            onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
          />
          <input
            className="input-field"
            placeholder="Description (optionnel)"
            value={form.description}
            onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
          />
          <select
            className="input-field"
            value={form.connection_id}
            onChange={e => setForm(f => ({ ...f, connection_id: e.target.value }))}
          >
            <option value="">Sélectionner une connexion *</option>
            {connections.map(c => (
              <option key={c.id} value={c.id}>{c.name} ({c.db_type})</option>
            ))}
          </select>
          <div className="flex gap-2">
            <button
              onClick={handleCreate}
              disabled={!form.name.trim() || !form.connection_id || createMut.isPending}
              className="btn-primary px-4 py-2"
            >
              {createMut.isPending ? 'Création...' : 'Créer'}
            </button>
            <button onClick={() => setShowForm(false)} className="btn-ghost px-4 py-2">Annuler</button>
          </div>
        </div>
      )}

      {/* List */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="card h-36 animate-pulse bg-gray-900" />
          ))}
        </div>
      ) : dashboards.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-gray-600 gap-3">
          <LayoutDashboard size={40} />
          <p>Aucun tableau de bord. Créez-en un !</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {dashboards.map(d => (
            <div key={d.id} className="card flex flex-col gap-3 hover:border-gray-700 transition-colors">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-100 truncate">{d.name}</p>
                  {d.description && <p className="text-xs text-gray-500 mt-0.5 truncate">{d.description}</p>}
                </div>
                <span className="shrink-0 text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded-full">
                  {d.widgets.length} widget{d.widgets.length !== 1 ? 's' : ''}
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-gray-500">
                <Database size={12} />
                <span>{connName(d.connection_id)}</span>
              </div>
              <div className="text-xs text-gray-600">
                {new Date(d.updated_at).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' })}
              </div>
              <div className="flex gap-2 mt-auto pt-2 border-t border-gray-800">
                <button
                  onClick={() => navigate(`/dashboards/${d.id}`)}
                  className="btn-ghost flex items-center gap-1.5 text-xs px-2 py-1"
                >
                  <ExternalLink size={12} /> Voir
                </button>
                <button
                  onClick={() => navigate(`/dashboards/${d.id}/edit`)}
                  className="btn-ghost flex items-center gap-1.5 text-xs px-2 py-1"
                >
                  <Edit2 size={12} /> Éditer
                </button>
                <button
                  onClick={() => { if (confirm(`Supprimer "${d.name}" ?`)) deleteMut.mutate(d.id) }}
                  className="btn-ghost flex items-center gap-1.5 text-xs px-2 py-1 text-red-500 hover:text-red-400 ml-auto"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
