import { useState, useRef, KeyboardEvent } from 'react'
import { BarChart2, Table2, Hash, Type, Loader } from 'lucide-react'
import type { WidgetType } from '../../api/types'

const WIDGET_TYPES: { type: WidgetType; icon: React.ReactNode; label: string }[] = [
  { type: 'chart', icon: <BarChart2 size={16} />, label: 'Graphique' },
  { type: 'table', icon: <Table2 size={16} />, label: 'Tableau' },
  { type: 'kpi', icon: <Hash size={16} />, label: 'KPI' },
  { type: 'text', icon: <Type size={16} />, label: 'Texte' },
]

interface Props {
  onAdd: (nlText: string, widgetType: WidgetType) => Promise<void>
  isLoading: boolean
}

export function AddWidgetPanel({ onAdd, isLoading }: Props) {
  const [text, setText] = useState('')
  const [selectedType, setSelectedType] = useState<WidgetType>('chart')
  const [error, setError] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = async () => {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return
    setError(null)
    try {
      await onAdd(trimmed, selectedType)
      setText('')
      if (textareaRef.current) textareaRef.current.style.height = 'auto'
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erreur lors de la génération')
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleInput = () => {
    const ta = textareaRef.current
    if (ta) {
      ta.style.height = 'auto'
      ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Ajouter une visualisation</p>

      {/* Type selector */}
      <div className="grid grid-cols-2 gap-2">
        {WIDGET_TYPES.map(({ type, icon, label }) => (
          <button
            key={type}
            onClick={() => setSelectedType(type)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
              selectedType === type
                ? 'bg-brand-600/30 text-brand-400 border border-brand-600/50'
                : 'bg-gray-800 text-gray-400 border border-transparent hover:border-gray-700'
            }`}
          >
            {icon}
            {label}
          </button>
        ))}
      </div>

      {/* NL input */}
      <div className="flex flex-col gap-2">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => { setText(e.target.value); handleInput() }}
          onKeyDown={handleKeyDown}
          placeholder={`Décrivez une visualisation...\nEx: Top 10 clients par chiffre d'affaires`}
          rows={3}
          disabled={isLoading}
          className="input-field resize-none text-sm leading-relaxed disabled:opacity-50"
        />
        <button
          onClick={handleSubmit}
          disabled={!text.trim() || isLoading}
          className="btn-primary flex items-center justify-center gap-2 py-2"
        >
          {isLoading ? <><Loader size={14} className="animate-spin" /> Génération...</> : 'Générer'}
        </button>
      </div>

      {error && (
        <p className="text-xs text-red-400 bg-red-900/20 border border-red-800/40 rounded p-2">
          {error}
        </p>
      )}
    </div>
  )
}
