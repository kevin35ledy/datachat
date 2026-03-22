import { useConnectionStore } from '../stores/connectionStore'
import { useChatStore } from '../stores/chatStore'
import { ChatWindow } from '../components/chat/ChatWindow'
import { QueryInput } from '../components/chat/QueryInput'
import { chatApi } from '../api/chat'
import { Link } from 'react-router-dom'
import { Plug } from 'lucide-react'

export function ChatPage() {
  const { activeConnectionId, activeConnection } = useConnectionStore()
  const { getMessages, addUserMessage, addAssistantMessage, isLoading, setLoading } = useChatStore()

  const sessionId = activeConnectionId ? `session-${activeConnectionId}` : 'default'
  const messages = getMessages(sessionId)

  const handleSend = async (text: string) => {
    if (!activeConnectionId) return
    setLoading(true)
    addUserMessage(sessionId, text)

    try {
      const response = await chatApi.send({
        text,
        connection_id: activeConnectionId,
        session_id: sessionId,
      })
      addAssistantMessage(sessionId, response.message_id, response)
    } catch (err) {
      const errorResponse = {
        message_id: crypto.randomUUID(),
        session_id: sessionId,
        nl_query: text,
        sql_query: null,
        result: null,
        chart_suggestion: null,
        summary: '',
        error: err instanceof Error ? err.message : 'Erreur inattendue',
        created_at: new Date().toISOString(),
      }
      addAssistantMessage(sessionId, errorResponse.message_id, errorResponse)
    } finally {
      setLoading(false)
    }
  }

  if (!activeConnectionId) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <Plug className="text-gray-700 mb-4" size={48} />
        <h2 className="text-lg font-semibold text-gray-400 mb-2">Aucune connexion active</h2>
        <p className="text-sm text-gray-600 mb-4">
          Connectez-vous à une base de données pour commencer
        </p>
        <Link to="/connections" className="btn-primary">
          Ajouter une connexion
        </Link>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 py-3 border-b border-gray-800 flex items-center gap-2">
        <span className="text-sm font-medium text-gray-300">{activeConnection?.name}</span>
        <span className="text-xs text-gray-600 bg-gray-800 px-2 py-0.5 rounded">
          {activeConnection?.db_type}
        </span>
      </div>

      <ChatWindow messages={messages} isLoading={isLoading} />
      <QueryInput
        onSend={handleSend}
        disabled={isLoading}
        placeholder={`Question sur ${activeConnection?.name ?? 'la base'}...`}
      />
    </div>
  )
}
