import { useEffect, useRef } from 'react'
import type { Message } from '../../stores/chatStore'
import { MessageBubble } from './MessageBubble'
import { Database } from 'lucide-react'

interface ChatWindowProps {
  messages: Message[]
  isLoading: boolean
}

export function ChatWindow({ messages, isLoading }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
        <Database className="text-gray-700 mb-4" size={48} />
        <h2 className="text-lg font-semibold text-gray-400 mb-2">
          Posez une question sur votre base de données
        </h2>
        <p className="text-sm text-gray-600 max-w-md">
          Exemples : &quot;Combien de clients avons-nous ?&quot;, &quot;Quelles sont les 10 commandes les plus récentes ?&quot;
        </p>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      {isLoading && (
        <div className="flex gap-3 justify-start">
          <div className="bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3">
            <div className="flex gap-1 items-center">
              <span className="w-2 h-2 bg-brand-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 bg-brand-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 bg-brand-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}
