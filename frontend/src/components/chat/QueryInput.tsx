import { useState, useRef, KeyboardEvent } from 'react'
import { Send } from 'lucide-react'

interface QueryInputProps {
  onSend: (text: string) => void
  disabled?: boolean
  placeholder?: string
}

export function QueryInput({ onSend, disabled, placeholder }: QueryInputProps) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = () => {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setText('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleInput = () => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 200) + 'px'
    }
  }

  return (
    <div className="border-t border-gray-800 px-4 py-3 bg-gray-900">
      <div className="flex items-end gap-2 bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 focus-within:ring-2 focus-within:ring-brand-500 focus-within:border-transparent transition-all">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          disabled={disabled}
          placeholder={placeholder ?? 'Posez une question sur vos données... (Entrée pour envoyer)'}
          rows={1}
          className="flex-1 bg-transparent text-sm text-gray-100 placeholder-gray-500 resize-none focus:outline-none min-h-[24px] max-h-[200px]"
        />
        <button
          onClick={handleSubmit}
          disabled={!text.trim() || disabled}
          className="shrink-0 text-brand-500 hover:text-brand-400 disabled:text-gray-600 transition-colors"
          title="Envoyer (Entrée)"
        >
          <Send size={18} />
        </button>
      </div>
      <p className="text-xs text-gray-600 mt-1.5 ml-1">Entrée pour envoyer · Maj+Entrée pour un saut de ligne</p>
    </div>
  )
}
