import { create } from 'zustand'

interface EffectPreviewState {
  /** The current FFmpeg filter string from the preview API. */
  filterString: string
  /** Whether a preview API call is in flight. */
  isLoading: boolean
  /** Error message from the last failed preview call. */
  error: string | null
  /** Object URL for the current effect preview thumbnail, or null. */
  thumbnailUrl: string | null
  /** File path of the video for the currently selected clip. */
  videoPath: string | null

  setFilterString: (filterString: string) => void
  setLoading: (isLoading: boolean) => void
  setError: (error: string | null) => void
  setThumbnailUrl: (url: string | null) => void
  setVideoPath: (videoPath: string | null) => void
  reset: () => void
}

export const useEffectPreviewStore = create<EffectPreviewState>((set, get) => ({
  filterString: '',
  isLoading: false,
  error: null,
  thumbnailUrl: null,
  videoPath: null,

  setFilterString: (filterString) => set({ filterString, error: null }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => {
    const prev = get().thumbnailUrl
    if (prev) URL.revokeObjectURL(prev)
    set({ error, isLoading: false, thumbnailUrl: null })
  },
  setThumbnailUrl: (url) => {
    const prev = get().thumbnailUrl
    if (prev) URL.revokeObjectURL(prev)
    set({ thumbnailUrl: url })
  },
  setVideoPath: (videoPath) => set({ videoPath }),
  reset: () => {
    const prev = get().thumbnailUrl
    if (prev) URL.revokeObjectURL(prev)
    set({ filterString: '', isLoading: false, error: null, thumbnailUrl: null, videoPath: null })
  },
}))
