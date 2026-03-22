import { NavLink } from 'react-router-dom'
import { MessageSquare, Database, Plug, LayoutDashboard } from 'lucide-react'
import { useConnectionStore } from '../../stores/connectionStore'
import clsx from 'clsx'

const navItems = [
  { to: '/chat', icon: MessageSquare, label: 'Chat' },
  { to: '/dashboards', icon: LayoutDashboard, label: 'Dashboards' },
  { to: '/connections', icon: Plug, label: 'Connexions' },
]

export function Sidebar() {
  const { connections, activeConnectionId, setActiveConnection } = useConnectionStore()

  return (
    <aside
      className="flex flex-col bg-gray-900 border-r border-gray-800"
      style={{ width: 'var(--sidebar-width)', minWidth: 'var(--sidebar-width)' }}
    >
      {/* Logo */}
      <div className="px-4 py-4 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <Database className="text-brand-500" size={20} />
          <span className="font-semibold text-gray-100 text-sm">DB-IA</span>
        </div>
      </div>

      {/* Active connection selector */}
      {connections.length > 0 && (
        <div className="px-3 py-3 border-b border-gray-800">
          <p className="text-xs text-gray-500 mb-2 uppercase tracking-wide">Base de données</p>
          <select
            value={activeConnectionId ?? ''}
            onChange={(e) => setActiveConnection(e.target.value || null)}
            className="input-field text-xs py-1.5"
          >
            <option value="">Sélectionner...</option>
            {connections.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                isActive
                  ? 'bg-brand-600/20 text-brand-400'
                  : 'text-gray-400 hover:text-gray-100 hover:bg-gray-800'
              )
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-gray-800">
        <p className="text-xs text-gray-600">DB-IA v0.1.0</p>
      </div>
    </aside>
  )
}
