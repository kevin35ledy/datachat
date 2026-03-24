import { useState, useRef, KeyboardEvent } from 'react'
import { BarChart2, Table2, Hash, Type, TableProperties, Loader, AlertTriangle, HelpCircle, ChevronRight } from 'lucide-react'
import type { WidgetType, ClarificationQuestion } from '../../api/types'

const WIDGET_TYPE_OPTIONS: { type: WidgetType; icon: React.ReactNode; label: string }[] = [
  { type: 'chart', icon: <BarChart2 size={16} />, label: 'Graphique' },
  { type: 'table', icon: <Table2 size={16} />, label: 'Tableau' },
  { type: 'pivot', icon: <TableProperties size={16} />, label: 'TCD' },
  { type: 'kpi', icon: <Hash size={16} />, label: 'KPI' },
  { type: 'text', icon: <Type size={16} />, label: 'Texte' },
]

interface Props {
  connectionId?: string
  onAdd: (nlText: string, widgetType: WidgetType) => Promise<void>
  onClarify?: (nlText: string) => Promise<ClarificationQuestion[]>
  isLoading: boolean
  warnings?: string[]
}

export function AddWidgetPanel({ connectionId, onAdd, onClarify, isLoading, warnings }: Props) {
  const [text, setText] = useState('')
  const [selectedType, setSelectedType] = useState<WidgetType>('chart')
  const [error, setError] = useState<string | null>(null)
  const [clarifying, setClarifying] = useState(false)
  const [questions, setQuestions] = useState<ClarificationQuestion[]>([])
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const buildEnrichedText = () => {
    if (questions.length === 0) return text.trim()
    const parts = questions
      .map(q => {
        const ans = answers[q.id]
        return ans ? `${q.question} → ${ans}` : null
      })
      .filter(Boolean)
    if (parts.length === 0) return text.trim()
    return `${text.trim()}\n\n[Précisions : ${parts.join(' | ')}]`
  }

  const handleAnalyze = async () => {
    const trimmed = text.trim()
    if (!trimmed || isLoading) return
    setError(null)

    if (onClarify && connectionId) {
      setClarifying(true)
      try {
        const qs = await onClarify(trimmed)
        if (qs.length > 0) {
          setQuestions(qs)
          setAnswers({})
          return // wait for user answers
        }
      } catch {
        // clarification failed silently → proceed directly
      } finally {
        setClarifying(false)
      }
    }

    // No questions → generate directly
    await doGenerate(trimmed)
  }

  const doGenerate = async (nlText: string) => {
    setError(null)
    try {
      await onAdd(nlText, selectedType)
      setText('')
      setQuestions([])
      setAnswers({})
      if (textareaRef.current) textareaRef.current.style.height = 'auto'
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erreur lors de la génération')
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (questions.length === 0) handleAnalyze()
    }
  }

  const handleInput = () => {
    const ta = textareaRef.current
    if (ta) {
      ta.style.height = 'auto'
      ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`
    }
  }

  const handleContinue = () => doGenerate(buildEnrichedText())

  return (
    <div className="flex flex-col gap-4">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Ajouter une visualisation</p>

      {/* Type selector */}
      <div className="grid grid-cols-3 gap-1.5">
        {WIDGET_TYPE_OPTIONS.map(({ type, icon, label }) => (
          <button
            key={type}
            onClick={() => setSelectedType(type)}
            className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-medium transition-colors ${
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
          onChange={(e) => { setText(e.target.value); handleInput(); setQuestions([]); setAnswers({}) }}
          onKeyDown={handleKeyDown}
          placeholder={`Décrivez une visualisation...\nEx: Top 10 clients par chiffre d'affaires`}
          rows={3}
          disabled={isLoading || clarifying}
          className="input-field resize-none text-sm leading-relaxed disabled:opacity-50"
        />
        {questions.length === 0 && (
          <button
            onClick={handleAnalyze}
            disabled={!text.trim() || isLoading || clarifying}
            className="btn-primary flex items-center justify-center gap-2 py-2"
          >
            {clarifying
              ? <><Loader size={14} className="animate-spin" /> Analyse...</>
              : isLoading
                ? <><Loader size={14} className="animate-spin" /> Génération...</>
                : 'Générer'}
          </button>
        )}
      </div>

      {/* Clarification questions */}
      {questions.length > 0 && (
        <div className="bg-amber-900/15 border border-amber-700/40 rounded-lg p-3 space-y-3">
          <div className="flex items-center gap-2 text-xs text-amber-300 font-medium">
            <HelpCircle size={13} />
            Précisions utiles avant génération
          </div>
          {questions.map(q => (
            <div key={q.id} className="space-y-1.5">
              <p className="text-xs text-gray-300">{q.question}</p>
              {q.context && <p className="text-[10px] text-gray-500 italic">{q.context}</p>}
              <div className="flex flex-wrap gap-1.5">
                {q.suggestions.map(s => (
                  <button
                    key={s}
                    onClick={() => setAnswers(prev => ({ ...prev, [q.id]: s }))}
                    className={`px-2 py-0.5 rounded text-xs transition-colors ${
                      answers[q.id] === s
                        ? 'bg-brand-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {s}
                  </button>
                ))}
                <input
                  type="text"
                  value={answers[q.id] && !q.suggestions.includes(answers[q.id]) ? answers[q.id] : ''}
                  onChange={e => setAnswers(prev => ({ ...prev, [q.id]: e.target.value }))}
                  placeholder="Autre..."
                  className="input-field text-xs py-0.5 w-24"
                />
              </div>
            </div>
          ))}
          <div className="flex gap-2 pt-1">
            <button
              onClick={handleContinue}
              disabled={isLoading}
              className="btn-primary text-xs py-1.5 flex items-center gap-1"
            >
              {isLoading ? <Loader size={12} className="animate-spin" /> : <ChevronRight size={12} />}
              {isLoading ? 'Génération...' : 'Continuer'}
            </button>
            <button
              onClick={() => { setQuestions([]); doGenerate(text.trim()) }}
              className="btn-ghost text-xs py-1.5"
            >
              Ignorer
            </button>
          </div>
        </div>
      )}

      {error && (
        <p className="text-xs text-red-400 bg-red-900/20 border border-red-800/40 rounded p-2">
          {error}
        </p>
      )}
      {warnings && warnings.length > 0 && (
        <div className="flex flex-col gap-1.5">
          {warnings.map((w, i) => (
            <div key={i} className="flex gap-2 text-xs text-amber-300 bg-amber-900/20 border border-amber-700/40 rounded p-2">
              <AlertTriangle size={13} className="shrink-0 mt-0.5" />
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
