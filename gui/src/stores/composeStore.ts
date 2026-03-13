import { create } from 'zustand'
import type { LayoutPosition, LayoutPreset, LayoutPresetListResponse } from '../types/timeline'
import { PRESET_POSITIONS } from '../data/presetPositions'

interface ComposeStoreState {
  /** Available layout presets. */
  presets: LayoutPreset[]
  /** Whether a fetch is in flight. */
  isLoading: boolean
  /** Error from the last API call. */
  error: string | null
  /** Currently selected preset name. */
  selectedPreset: string | null
  /** Custom positions for manual coordinate entry. */
  customPositions: LayoutPosition[]

  /** Fetch available layout presets. */
  fetchPresets: () => Promise<void>
  /** Select a preset by name. */
  selectPreset: (name: string) => void
  /** Update custom positions directly. */
  setCustomPositions: (positions: LayoutPosition[]) => void
  /** Update a single custom position field. */
  updateCustomPosition: (index: number, field: keyof LayoutPosition, value: number) => void
  /** Get the active positions (from selected preset or custom). */
  getActivePositions: () => LayoutPosition[]
  /** Reset store state. */
  reset: () => void
}

export const useComposeStore = create<ComposeStoreState>((set, get) => ({
  presets: [],
  isLoading: false,
  error: null,
  selectedPreset: null,
  customPositions: [],

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

  selectPreset: (name: string) => {
    const positions = PRESET_POSITIONS[name]
    if (positions) {
      set({
        selectedPreset: name,
        customPositions: positions.map((p) => ({ ...p })),
      })
    }
  },

  setCustomPositions: (positions: LayoutPosition[]) => {
    set({ customPositions: positions, selectedPreset: null })
  },

  updateCustomPosition: (index: number, field: keyof LayoutPosition, value: number) => {
    const { customPositions } = get()
    if (index < 0 || index >= customPositions.length) return
    const clamped = field === 'z_index' ? Math.round(value) : Math.min(1, Math.max(0, value))
    const updated = customPositions.map((pos, i) =>
      i === index ? { ...pos, [field]: clamped } : pos,
    )
    set({ customPositions: updated, selectedPreset: null })
  },

  getActivePositions: () => {
    const { selectedPreset, customPositions } = get()
    if (selectedPreset && PRESET_POSITIONS[selectedPreset]) {
      return PRESET_POSITIONS[selectedPreset]
    }
    return customPositions
  },

  reset: () =>
    set({
      presets: [],
      isLoading: false,
      error: null,
      selectedPreset: null,
      customPositions: [],
    }),
}))
