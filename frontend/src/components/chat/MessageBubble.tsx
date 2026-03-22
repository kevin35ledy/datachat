import type { Message } from '../../stores/chatStore'
import { SQLPreview } from './SQLPreview'
import { ResultTable } from './ResultTable'
import { AlertCircle, CheckCircle } from 'lucide-react'

interface MessageBubbleProps {
  message: Message
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const response = message.response

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="bg-brand-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-xl text-sm">
          {message.text}
        </div>
      </div>
    )
  }

  // Assistant message
  const hasError = !!response?.error
  const hasResult = !!response?.result

  return (
    <div className="flex justify-start">
      <div className="bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3 max-w-4xl w-full space-y-3">
        {/* Error state */}
        {hasError && (
          <div className="flex items-start gap-2 text-red-400 text-sm">
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            <span>{response!.error}</span>
          </div>
        )}

        {/* Summary */}
        {response?.summary && !hasError && (
          <p className="text-sm text-gray-200">{response.summary}</p>
        )}

        {/* SQL Preview */}
        {response?.sql_query?.validated_sql && (
          <SQLPreview
            sql={response.sql_query.validated_sql}
            explanation={response.sql_query.explanation}
            confidence={response.sql_query.confidence}
            executionMs={response.result?.execution_time_ms}
          />
        )}

        {/* Results */}
        {hasResult && response!.result!.total_count > 0 && (
          <ResultTable result={response!.result!} />
        )}

        {/* No results */}
        {hasResult && response!.result!.total_count === 0 && !hasError && (
          <div className="flex items-center gap-2 text-gray-500 text-sm">
            <CheckCircle size={14} />
            <span>Aucun résultat trouvé.</span>
          </div>
        )}
      </div>
    </div>
  )
}
