import { create } from 'zustand'
import type { LayoutPreset, LayoutPresetListResponse } from '../types/timeline'

interface ComposeStoreState {
  /** Available layout presets. */
  presets: LayoutPreset[]
  /** Whether a fetch is in flight. */
  isLoading: boolean
  /** Error from the last API call. */
  error: string | null

  /** Fetch available layout presets. */
  fetchPresets: () => Promise<void>
  /** Reset store state. */
  reset: () => void
}

export const useComposeStore = create<ComposeStoreState>((set) => ({
  presets: [],
  isLoading: false,
  error: null,

  fetchPresets: async () => {
    set({ isLoading: true, error: null })
    try {
      const res = await fetch('/api/v1/compose/presets')
      if (!res.ok) {
        const detail = await res.json().catch(() => null)
        throw new Error(detail?.detail?.message ?? `Fetch presets failed: ${res.status}`)
      }
      const data: LayoutPresetListResponse = await res.json()
      set({ presets: data.presets, isLoading: false })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Unknown error',
        isLoading: false,
      })
    }
  },

  reset: () => set({ presets: [], isLoading: false, error: null }),
}))
