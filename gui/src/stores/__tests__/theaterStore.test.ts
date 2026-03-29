import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useTheaterStore } from '../theaterStore'

beforeEach(() => {
  vi.restoreAllMocks()
  useTheaterStore.getState().reset()
})

describe('theaterStore', () => {
  it('initializes with correct defaults', () => {
    const state = useTheaterStore.getState()
    expect(state.isFullscreen).toBe(false)
    expect(state.isHUDVisible).toBe(true)
    expect(state.lastMouseMoveTime).toBe(0)
  })

  describe('enterTheater', () => {
    it('sets isFullscreen to true and shows HUD', () => {
      const before = Date.now()
      useTheaterStore.getState().enterTheater()
      const state = useTheaterStore.getState()
      expect(state.isFullscreen).toBe(true)
      expect(state.isHUDVisible).toBe(true)
      expect(state.lastMouseMoveTime).toBeGreaterThanOrEqual(before)
    })
  })

  describe('exitTheater', () => {
    it('resets all state to defaults', () => {
      useTheaterStore.getState().enterTheater()
      useTheaterStore.getState().exitTheater()
      const state = useTheaterStore.getState()
      expect(state.isFullscreen).toBe(false)
      expect(state.isHUDVisible).toBe(true)
      expect(state.lastMouseMoveTime).toBe(0)
    })
  })

  describe('showHUD', () => {
    it('sets isHUDVisible to true and updates timestamp', () => {
      useTheaterStore.setState({ isHUDVisible: false })
      const before = Date.now()
      useTheaterStore.getState().showHUD()
      const state = useTheaterStore.getState()
      expect(state.isHUDVisible).toBe(true)
      expect(state.lastMouseMoveTime).toBeGreaterThanOrEqual(before)
    })
  })

  describe('hideHUD', () => {
    it('sets isHUDVisible to false', () => {
      useTheaterStore.getState().hideHUD()
      expect(useTheaterStore.getState().isHUDVisible).toBe(false)
    })
  })

  describe('reset', () => {
    it('resets all state to initial values', () => {
      useTheaterStore.setState({
        isFullscreen: true,
        isHUDVisible: false,
        lastMouseMoveTime: 12345,
      })
      useTheaterStore.getState().reset()
      const state = useTheaterStore.getState()
      expect(state.isFullscreen).toBe(false)
      expect(state.isHUDVisible).toBe(true)
      expect(state.lastMouseMoveTime).toBe(0)
    })
  })
})
