import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/shared/Layout'
import { ChatPage } from './pages/ChatPage'
import { ConnectionsPage } from './pages/ConnectionsPage'
import { ConnectionAnnotationsPage } from './pages/ConnectionAnnotationsPage'
import { DashboardsPage } from './pages/DashboardsPage'
import { DashboardViewPage } from './pages/DashboardViewPage'
import { DashboardBuilderPage } from './pages/DashboardBuilderPage'
import { useThemeStore } from './stores/themeStore'

export default function App() {
  const { theme } = useThemeStore()

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/chat" replace />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="connections" element={<ConnectionsPage />} />
          <Route path="connections/:connId/annotate" element={<ConnectionAnnotationsPage />} />
          <Route path="dashboards" element={<DashboardsPage />} />
          <Route path="dashboards/:dashboardId" element={<DashboardViewPage />} />
          <Route path="dashboards/:dashboardId/edit" element={<DashboardBuilderPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
