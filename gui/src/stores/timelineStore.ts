import { create } from 'zustand'
import type { TimelineResponse, Track } from '../types/timeline'

interface TimelineStoreState {
  /** Tracks for the current project timeline. */
  tracks: Track[]
  /** Total timeline duration in seconds. */
  duration: number
  /** Timeline version number. */
  version: number
  /** Whether a fetch is in flight. */
  isLoading: boolean
  /** Error from the last API call. */
  error: string | null
  /** ID of the currently selected clip, or null if none selected. */
  selectedClipId: string | null
  /** Current playhead position in seconds. */
  playheadPosition: number

  /** Fetch timeline for a project. */
  fetchTimeline: (projectId: string) => Promise<void>
  /** Set the selected clip by ID (null to deselect). */
  selectClip: (clipId: string | null) => void
  /** Set the playhead position in seconds. */
  setPlayheadPosition: (position: number) => void
  /** Reset store state. */
  reset: () => void
}

export const useTimelineStore = create<TimelineStoreState>((set) => ({
  tracks: [],
  duration: 0,
  version: 0,
  isLoading: false,
  error: null,
  selectedClipId: null,
  playheadPosition: 0,

  fetchTimeline: async (projectId) => {
    set({ isLoading: true, error: null })
    try {
      const res = await fetch(`/api/v1/projects/${projectId}/timeline`)
      if (!res.ok) {
        const detail = await res.json().catch(() => null)
        throw new Error(detail?.detail?.message ?? `Fetch timeline failed: ${res.status}`)
      }
      const data: TimelineResponse = await res.json()
      set({
        tracks: data.tracks,
        duration: data.duration,
        version: data.version,
        isLoading: false,
      })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Unknown error',
        isLoading: false,
      })
    }
  },

  selectClip: (clipId) => set({ selectedClipId: clipId }),

  setPlayheadPosition: (position) => set({ playheadPosition: position }),

  reset: () =>
    set({
      tracks: [],
      duration: 0,
      version: 0,
      isLoading: false,
      error: null,
      selectedClipId: null,
      playheadPosition: 0,
    }),
}))
