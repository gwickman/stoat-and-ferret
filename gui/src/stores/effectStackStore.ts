import { create } from 'zustand'

/** An applied effect entry as stored on a clip. */
export interface AppliedEffect {
  effect_type: string
  parameters: Record<string, unknown>
  filter_string: string
}

interface EffectStackState {
  /** Currently selected clip ID. */
  selectedClipId: string | null
  /** Effects for the currently selected clip. */
  effects: AppliedEffect[]
  /** Whether a fetch is in flight. */
  isLoading: boolean
  /** Error from the last API call. */
  error: string | null

  selectClip: (clipId: string | null) => void
  setEffects: (effects: AppliedEffect[]) => void
  setLoading: (isLoading: boolean) => void
  setError: (error: string | null) => void
  /** Fetch effects for the selected clip from the API. */
  fetchEffects: (projectId: string, clipId: string) => Promise<void>
  /** Remove an effect by index via DELETE API call. */
  removeEffect: (projectId: string, clipId: string, index: number) => Promise<void>
  reset: () => void
}

export const useEffectStackStore = create<EffectStackState>((set, get) => ({
  selectedClipId: null,
  effects: [],
  isLoading: false,
  error: null,

  selectClip: (clipId) => set({ selectedClipId: clipId, effects: [], error: null }),

  setEffects: (effects) => set({ effects }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error, isLoading: false }),

  fetchEffects: async (projectId, clipId) => {
    set({ isLoading: true, error: null })
    try {
      const res = await fetch(`/api/v1/projects/${projectId}/clips`)
      if (!res.ok) throw new Error(`Fetch clips failed: ${res.status}`)
      const json = await res.json()
      const clip = json.clips?.find((c: { id: string }) => c.id === clipId)
      set({
        effects: clip?.effects ?? [],
        isLoading: false,
      })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Unknown error',
        isLoading: false,
      })
    }
  },

  removeEffect: async (projectId, clipId, index) => {
    try {
      const res = await fetch(
        `/api/v1/projects/${projectId}/clips/${clipId}/effects/${index}`,
        { method: 'DELETE' },
      )
      if (!res.ok) throw new Error(`Delete failed: ${res.status}`)
      // Refresh the effect list
      await get().fetchEffects(projectId, clipId)
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Unknown error',
      })
    }
  },

  reset: () =>
    set({
      selectedClipId: null,
      effects: [],
      isLoading: false,
      error: null,
    }),
}))
