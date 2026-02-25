import { create } from 'zustand'

interface TransitionState {
  /** Source clip ID for the transition. */
  sourceClipId: string | null
  /** Target clip ID for the transition. */
  targetClipId: string | null

  /** Set source clip, clearing any existing target. */
  selectSource: (clipId: string) => void
  /** Set target clip. */
  selectTarget: (clipId: string) => void
  /** Whether both source and target are selected. */
  isReady: () => boolean
  /** Clear both selections. */
  reset: () => void
}

export const useTransitionStore = create<TransitionState>((set, get) => ({
  sourceClipId: null,
  targetClipId: null,

  selectSource: (clipId) => set({ sourceClipId: clipId, targetClipId: null }),
  selectTarget: (clipId) => set({ targetClipId: clipId }),
  isReady: () => get().sourceClipId !== null && get().targetClipId !== null,
  reset: () => set({ sourceClipId: null, targetClipId: null }),
}))
