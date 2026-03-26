import { create } from 'zustand'

export type PreviewStatus =
  | 'initializing'
  | 'generating'
  | 'ready'
  | 'seeking'
  | 'error'
  | 'expired'

export type PreviewQuality = 'low' | 'medium' | 'high'

interface PreviewState {
  /** Active preview session ID, or null if no session. */
  sessionId: string | null
  /** Current session status. */
  status: PreviewStatus | null
  /** Preview quality level. */
  quality: PreviewQuality
  /** Current playback position in seconds. */
  position: number
  /** Total duration in seconds. */
  duration: number
  /** Volume level, clamped to [0.0, 1.0]. */
  volume: number
  /** Whether audio is muted. */
  muted: boolean
  /** Generation progress, 0.0 to 1.0. */
  progress: number
  /** Error message, or null. */
  error: string | null

  connect: (projectId: string) => Promise<void>
  disconnect: () => void
  setQuality: (projectId: string, quality: PreviewQuality) => Promise<void>
  setVolume: (volume: number) => void
  setMuted: (muted: boolean) => void
  setPosition: (position: number) => void
  setProgress: (progress: number) => void
  setStatus: (status: PreviewStatus) => void
  setError: (error: string | null) => void
  reset: () => void
}

const VALID_QUALITIES: PreviewQuality[] = ['low', 'medium', 'high']

const initialState = {
  sessionId: null,
  status: null,
  quality: 'medium' as PreviewQuality,
  position: 0,
  duration: 0,
  volume: 1.0,
  muted: false,
  progress: 0,
  error: null,
}

export const usePreviewStore = create<PreviewState>((set, get) => ({
  ...initialState,

  connect: async (projectId: string) => {
    set({ status: 'initializing', error: null })
    try {
      const res = await fetch(`/api/v1/projects/${projectId}/preview/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quality: get().quality }),
      })
      if (!res.ok) {
        const detail = await res.json().catch(() => null)
        set({
          status: 'error',
          error: detail?.detail ?? `Preview start failed: ${res.status}`,
        })
        return
      }
      const data = await res.json()
      set({ sessionId: data.session_id, status: 'generating' })
    } catch (err) {
      set({
        status: 'error',
        error: err instanceof Error ? err.message : 'Unknown error',
      })
    }
  },

  disconnect: () => {
    const { sessionId } = get()
    if (sessionId) {
      fetch(`/api/v1/preview/${sessionId}`, { method: 'DELETE' }).catch(() => {})
    }
    set({ ...initialState })
  },

  setQuality: async (projectId: string, quality: PreviewQuality) => {
    if (!VALID_QUALITIES.includes(quality)) return
    // Disconnect existing session and start a new one at the new quality
    const { sessionId } = get()
    if (sessionId) {
      fetch(`/api/v1/preview/${sessionId}`, { method: 'DELETE' }).catch(() => {})
    }
    set({ quality, sessionId: null, status: 'initializing', error: null, progress: 0 })
    try {
      const res = await fetch(`/api/v1/projects/${projectId}/preview/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quality }),
      })
      if (!res.ok) {
        const detail = await res.json().catch(() => null)
        set({
          status: 'error',
          error: detail?.detail ?? `Preview start failed: ${res.status}`,
        })
        return
      }
      const data = await res.json()
      set({ sessionId: data.session_id, status: 'generating' })
    } catch (err) {
      set({
        status: 'error',
        error: err instanceof Error ? err.message : 'Unknown error',
      })
    }
  },

  setVolume: (volume: number) => {
    set({ volume: Math.max(0, Math.min(1, volume)) })
  },

  setMuted: (muted: boolean) => set({ muted }),

  setPosition: (position: number) => {
    const { duration } = get()
    set({ position: Math.max(0, Math.min(position, duration)) })
  },

  setProgress: (progress: number) => {
    set({ progress: Math.max(0, Math.min(1, progress)) })
  },

  setStatus: (status: PreviewStatus) => set({ status }),

  setError: (error: string | null) => set({ error }),

  reset: () => set({ ...initialState }),
}))
