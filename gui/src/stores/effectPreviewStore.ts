import { create } from 'zustand'

interface EffectPreviewState {
  /** The current FFmpeg filter string from the preview API. */
  filterString: string
  /** Whether a preview API call is in flight. */
  isLoading: boolean
  /** Error message from the last failed preview call. */
  error: string | null

  setFilterString: (filterString: string) => void
  setLoading: (isLoading: boolean) => void
  setError: (error: string | null) => void
  reset: () => void
}

export const useEffectPreviewStore = create<EffectPreviewState>((set) => ({
  filterString: '',
  isLoading: false,
  error: null,

  setFilterString: (filterString) => set({ filterString, error: null }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error, isLoading: false }),
  reset: () => set({ filterString: '', isLoading: false, error: null }),
}))
