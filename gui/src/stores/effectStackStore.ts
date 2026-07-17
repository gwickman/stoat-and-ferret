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
  /**
   * Client-generated ids kept in lockstep with `effects` (same length, same
   * index correspondence) so `EffectStack` rows keep stable DOM identity
   * across the async delete/refetch boundary. Never regenerated for a
   * position that already has one at the start of a `fetchEffects` call.
   */
  clientIds: string[]
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
  clientIds: [],
  isLoading: false,
  error: null,

  selectClip: (clipId) =>
    set({ selectedClipId: clipId, effects: [], clientIds: [], error: null }),

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
      const newEffects: AppliedEffect[] = clip?.effects ?? []
      const currentClientIds = get().clientIds
      // Covers initial fetch (currentClientIds empty), same-length fetch
      // (0 new ids generated), and append fetch (prefix preserved, new ids
      // generated only for the new tail entries) in one branch.
      const newClientIds =
        newEffects.length >= currentClientIds.length
          ? [
              ...currentClientIds,
              ...Array.from(
                { length: newEffects.length - currentClientIds.length },
                () => crypto.randomUUID(),
              ),
            ]
          : newEffects.map(() => crypto.randomUUID())
      set({
        effects: newEffects,
        clientIds: newClientIds,
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
      // Splice the deleted index out of both arrays in the same lockstep
      // operation instead of re-fetching — a re-fetch would let a
      // same-length fetch race the async window (INV-001).
      set((state) => ({
        effects: state.effects.filter((_, i) => i !== index),
        clientIds: state.clientIds.filter((_, i) => i !== index),
      }))
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
      clientIds: [],
      isLoading: false,
      error: null,
    }),
}))
