import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ConnectionConfig } from '../api/types'

interface ConnectionStore {
  connections: ConnectionConfig[]
  activeConnectionId: string | null

  setConnections: (connections: ConnectionConfig[]) => void
  addConnection: (connection: ConnectionConfig) => void
  removeConnection: (id: string) => void
  setActiveConnection: (id: string | null) => void
  get activeConnection(): ConnectionConfig | undefined
}

export const useConnectionStore = create<ConnectionStore>()(
  persist(
    (set, get) => ({
      connections: [],
      activeConnectionId: null,

      setConnections: (connections) => set({ connections }),
      addConnection: (connection) =>
        set((state) => ({ connections: [...state.connections, connection] })),
      removeConnection: (id) =>
        set((state) => ({
          connections: state.connections.filter((c) => c.id !== id),
          activeConnectionId: state.activeConnectionId === id ? null : state.activeConnectionId,
        })),
      setActiveConnection: (id) => set({ activeConnectionId: id }),

      get activeConnection() {
        return get().connections.find((c) => c.id === get().activeConnectionId)
      },
    }),
    { name: 'datachat-connections' }
  )
)
