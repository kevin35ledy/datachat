import { NavLink } from 'react-router-dom'
import { MessageSquare, Database, Plug, LayoutDashboard } from 'lucide-react'
import { useConnectionStore } from '../../stores/connectionStore'
import { useThemeStore, type Theme } from '../../stores/themeStore'
import clsx from 'clsx'

const THEMES: { id: Theme; color: string; label: string }[] = [
  { id: 'cyan',   color: '#0ea5e9', label: 'Cyan' },
  { id: 'violet', color: '#a855f7', label: 'Violet' },
  { id: 'amber',  color: '#f59e0b', label: 'Ambre' },
]

const navItems = [
  { to: '/chat', icon: MessageSquare, label: 'Chat' },
  { to: '/dashboards', icon: LayoutDashboard, label: 'Dashboards' },
  { to: '/connections', icon: Plug, label: 'Connexions' },
]

export function Sidebar() {
  const { connections, activeConnectionId, setActiveConnection } = useConnectionStore()
  const { theme, setTheme } = useThemeStore()

  return (
    <aside
      className="flex flex-col bg-gray-900 border-r border-gray-800"
      style={{ width: 'var(--sidebar-width)', minWidth: 'var(--sidebar-width)' }}
    >
      {/* Logo */}
      <div className="px-4 py-4 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <Database className="text-brand-500" size={20} />
          <span className="font-semibold text-gray-100 text-sm">DataChat</span>
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

      {/* Theme selector */}
      <div className="px-4 py-3 border-t border-gray-800">
        <p className="text-xs text-gray-600 mb-2">Thème</p>
        <div className="flex gap-2">
          {THEMES.map((t) => (
            <button
              key={t.id}
              onClick={() => setTheme(t.id)}
              title={t.label}
              className={clsx(
                'w-5 h-5 rounded-full transition-all',
                theme === t.id && 'ring-2 ring-offset-2 ring-offset-gray-900 ring-white'
              )}
              style={{ backgroundColor: t.color }}
            />
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-gray-800">
        <p className="text-xs text-gray-600">DataChat v0.1.0</p>
      </div>
    </aside>
  )
}
