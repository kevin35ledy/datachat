import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/shared/Layout'
import { ChatPage } from './pages/ChatPage'
import { ConnectionsPage } from './pages/ConnectionsPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/chat" replace />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="connections" element={<ConnectionsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
