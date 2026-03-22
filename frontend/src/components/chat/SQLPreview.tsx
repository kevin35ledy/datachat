import { useState } from 'react'
import { ChevronDown, ChevronRight, Copy, Check, Clock } from 'lucide-react'

interface SQLPreviewProps {
  sql: string
  explanation?: string
  confidence?: number
  executionMs?: number
}

export function SQLPreview({ sql, explanation, confidence, executionMs }: SQLPreviewProps) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(sql)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const isLowConfidence = confidence !== undefined && confidence < 0.6

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden text-xs">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 w-full px-3 py-2 bg-gray-900 hover:bg-gray-800 transition-colors text-left"
      >
        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        <span className="text-gray-400 font-mono">SQL généré</span>
        {executionMs !== undefined && (
          <span className="flex items-center gap-1 text-gray-600 ml-auto">
            <Clock size={10} />
            {executionMs}ms
          </span>
        )}
        {isLowConfidence && (
          <span className="bg-yellow-900/50 text-yellow-400 px-2 py-0.5 rounded text-xs ml-1">
            Faible confiance
          </span>
        )}
      </button>

      {expanded && (
        <>
          {/* Explanation */}
          {explanation && (
            <div className="px-3 py-2 bg-gray-900/50 text-gray-400 text-xs border-b border-gray-700">
              {explanation}
            </div>
          )}

          {/* SQL Code */}
          <div className="relative">
            <pre className="px-3 py-3 bg-gray-950 text-green-400 font-mono overflow-x-auto text-xs leading-relaxed">
              {sql}
            </pre>
            <button
              onClick={handleCopy}
              className="absolute top-2 right-2 text-gray-600 hover:text-gray-300 transition-colors"
              title="Copier le SQL"
            >
              {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
            </button>
          </div>
        </>
      )}
    </div>
  )
}
