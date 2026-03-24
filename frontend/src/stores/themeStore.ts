import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Theme = 'cyan' | 'violet' | 'amber'

interface ThemeStore {
  theme: Theme
  setTheme: (theme: Theme) => void
}

export const useThemeStore = create<ThemeStore>()(
  persist(
    (set) => ({
      theme: 'cyan',
      setTheme: (theme) => set({ theme }),
    }),
    { name: 'datachat-theme' }
  )
)
