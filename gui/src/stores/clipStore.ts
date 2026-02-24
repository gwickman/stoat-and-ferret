import { create } from 'zustand'
import {
  type Clip,
  createClip as apiCreateClip,
  deleteClip as apiDeleteClip,
  fetchClips as apiFetchClips,
  updateClip as apiUpdateClip,
} from '../hooks/useProjects'

interface ClipStoreState {
  /** Clips for the current project. */
  clips: Clip[]
  /** Whether a CRUD operation is in flight. */
  isLoading: boolean
  /** Error from the last API call. */
  error: string | null

  /** Fetch all clips for a project. */
  fetchClips: (projectId: string) => Promise<void>
  /** Create a new clip. */
  createClip: (
    projectId: string,
    data: {
      source_video_id: string
      in_point: number
      out_point: number
      timeline_position: number
    },
  ) => Promise<void>
  /** Update an existing clip. */
  updateClip: (
    projectId: string,
    clipId: string,
    data: {
      in_point?: number
      out_point?: number
      timeline_position?: number
    },
  ) => Promise<void>
  /** Delete a clip. */
  deleteClip: (projectId: string, clipId: string) => Promise<void>
  /** Reset store state. */
  reset: () => void
}

export const useClipStore = create<ClipStoreState>((set, get) => ({
  clips: [],
  isLoading: false,
  error: null,

  fetchClips: async (projectId) => {
    set({ isLoading: true, error: null })
    try {
      const result = await apiFetchClips(projectId)
      set({ clips: result.clips, isLoading: false })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Unknown error',
        isLoading: false,
      })
    }
  },

  createClip: async (projectId, data) => {
    set({ isLoading: true, error: null })
    try {
      await apiCreateClip(projectId, data)
      await get().fetchClips(projectId)
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Unknown error',
        isLoading: false,
      })
      throw err
    }
  },

  updateClip: async (projectId, clipId, data) => {
    set({ isLoading: true, error: null })
    try {
      await apiUpdateClip(projectId, clipId, data)
      await get().fetchClips(projectId)
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Unknown error',
        isLoading: false,
      })
      throw err
    }
  },

  deleteClip: async (projectId, clipId) => {
    set({ isLoading: true, error: null })
    try {
      await apiDeleteClip(projectId, clipId)
      await get().fetchClips(projectId)
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Unknown error',
        isLoading: false,
      })
      throw err
    }
  },

  reset: () => set({ clips: [], isLoading: false, error: null }),
}))
