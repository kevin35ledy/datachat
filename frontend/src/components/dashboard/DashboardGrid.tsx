import type { DashboardWidget, QueryResult } from '../../api/types'
import { Widget } from './Widget'

const COL_SPAN: Record<1 | 2 | 3, string> = {
  1: 'col-span-12 md:col-span-4',
  2: 'col-span-12 md:col-span-6',
  3: 'col-span-12',
}

interface Props {
  widgets: DashboardWidget[]
  widgetResults: Record<string, QueryResult | string>
  widgetLoading: Record<string, boolean>
  isEditing?: boolean
  onDeleteWidget?: (id: string) => void
  onMoveWidget?: (id: string, dir: 'up' | 'down') => void
  onResizeWidget?: (id: string, width: 1 | 2 | 3) => void
}

export function DashboardGrid({ widgets, widgetResults, widgetLoading, isEditing, onDeleteWidget, onMoveWidget, onResizeWidget }: Props) {
  const sorted = [...widgets].sort((a, b) => a.position - b.position)

  if (sorted.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-gray-600">
        <p className="text-lg">Ce tableau de bord est vide.</p>
        {isEditing && <p className="text-sm mt-1">Décrivez une visualisation dans le panneau gauche.</p>}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-12 gap-4">
      {sorted.map((widget) => {
        const raw = widgetResults[widget.id]
        const result = raw && typeof raw !== 'string' ? raw : undefined
        const error = typeof raw === 'string' ? raw : undefined

        return (
          <div key={widget.id} className={COL_SPAN[widget.width]}>
            <Widget
              widget={widget}
              result={result}
              error={error}
              isLoading={widgetLoading[widget.id] ?? false}
              isEditing={isEditing}
              onDelete={onDeleteWidget}
              onMoveUp={(id) => onMoveWidget?.(id, 'up')}
              onMoveDown={(id) => onMoveWidget?.(id, 'down')}
              onResizeWidth={onResizeWidget}
            />
          </div>
        )
      })}
    </div>
  )
}
