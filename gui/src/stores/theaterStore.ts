import { create } from 'zustand'

interface TheaterState {
  /** Whether the theater mode is currently in fullscreen. */
  isFullscreen: boolean
  /** Whether the HUD overlay is currently visible. */
  isHUDVisible: boolean
  /** Timestamp of the last mouse movement (ms since epoch). */
  lastMouseMoveTime: number

  enterTheater: () => void
  exitTheater: () => void
  showHUD: () => void
  hideHUD: () => void
  reset: () => void
}

const initialState = {
  isFullscreen: false,
  isHUDVisible: true,
  lastMouseMoveTime: 0,
}

export const useTheaterStore = create<TheaterState>((set) => ({
  ...initialState,

  enterTheater: () => set({ isFullscreen: true, isHUDVisible: true, lastMouseMoveTime: Date.now() }),

  exitTheater: () => set({ ...initialState }),

  showHUD: () => set({ isHUDVisible: true, lastMouseMoveTime: Date.now() }),

  hideHUD: () => set({ isHUDVisible: false }),

  reset: () => set({ ...initialState }),
}))
