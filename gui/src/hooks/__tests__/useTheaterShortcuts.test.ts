import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useTheaterShortcuts } from '../useTheaterShortcuts'
import { usePreviewStore } from '../../stores/previewStore'

function createMockVideo(overrides: Partial<HTMLVideoElement> = {}) {
  return {
    paused: true,
    muted: false,
    currentTime: 10,
    duration: 60,
    play: vi.fn().mockResolvedValue(undefined),
    pause: vi.fn(),
    ...overrides,
  } as unknown as HTMLVideoElement
}

function fireKey(key: string) {
  const event = new KeyboardEvent('keydown', { key, bubbles: true })
  document.dispatchEvent(event)
}

describe('useTheaterShortcuts', () => {
  let onExit: ReturnType<typeof vi.fn>
  let onToggleFullscreen: ReturnType<typeof vi.fn>

  beforeEach(() => {
    vi.restoreAllMocks()
    usePreviewStore.getState().reset()
    onExit = vi.fn()
    onToggleFullscreen = vi.fn()
  })

  function renderWithVideo(video: HTMLVideoElement, enabled = true) {
    const ref = { current: video }
    return renderHook(() =>
      useTheaterShortcuts({
        videoRef: ref,
        onExit: onExit as () => void,
        onToggleFullscreen: onToggleFullscreen as () => void,
        enabled,
      }),
    )
  }

  // FR-001: Space toggles play/pause
  describe('Space — play/pause', () => {
    it('plays when paused', () => {
      const video = createMockVideo({ paused: true })
      renderWithVideo(video)
      fireKey(' ')
      expect(video.play).toHaveBeenCalled()
    })

    it('pauses when playing', () => {
      const video = createMockVideo({ paused: false })
      renderWithVideo(video)
      fireKey(' ')
      expect(video.pause).toHaveBeenCalled()
    })
  })

  // FR-002: Escape exits Theater Mode
  it('Escape calls onExit', () => {
    const video = createMockVideo()
    renderWithVideo(video)
    fireKey('Escape')
    expect(onExit).toHaveBeenCalled()
  })

  // FR-003: F toggles fullscreen
  describe('F — fullscreen toggle', () => {
    it('calls onToggleFullscreen on lowercase f', () => {
      const video = createMockVideo()
      renderWithVideo(video)
      fireKey('f')
      expect(onToggleFullscreen).toHaveBeenCalled()
    })

    it('calls onToggleFullscreen on uppercase F', () => {
      const video = createMockVideo()
      renderWithVideo(video)
      fireKey('F')
      expect(onToggleFullscreen).toHaveBeenCalled()
    })
  })

  // FR-004: M toggles mute
  describe('M — mute toggle', () => {
    it('mutes when unmuted', () => {
      const video = createMockVideo({ muted: false })
      renderWithVideo(video)
      fireKey('m')
      expect(video.muted).toBe(true)
      expect(usePreviewStore.getState().muted).toBe(true)
    })

    it('unmutes when muted', () => {
      const video = createMockVideo({ muted: true })
      renderWithVideo(video)
      fireKey('M')
      expect(video.muted).toBe(false)
      expect(usePreviewStore.getState().muted).toBe(false)
    })
  })

  // FR-005: Left/Right arrows seek ±5 seconds
  describe('Arrow keys — seek', () => {
    it('ArrowLeft seeks backward 5 seconds', () => {
      const video = createMockVideo({ currentTime: 10, duration: 60 })
      renderWithVideo(video)
      fireKey('ArrowLeft')
      expect(video.currentTime).toBe(5)
    })

    it('ArrowRight seeks forward 5 seconds', () => {
      const video = createMockVideo({ currentTime: 10, duration: 60 })
      renderWithVideo(video)
      fireKey('ArrowRight')
      expect(video.currentTime).toBe(15)
    })

    it('ArrowLeft clamps to 0', () => {
      const video = createMockVideo({ currentTime: 2, duration: 60 })
      renderWithVideo(video)
      fireKey('ArrowLeft')
      expect(video.currentTime).toBe(0)
    })

    it('ArrowRight clamps to duration', () => {
      const video = createMockVideo({ currentTime: 58, duration: 60 })
      renderWithVideo(video)
      fireKey('ArrowRight')
      expect(video.currentTime).toBe(60)
    })
  })

  // FR-006: Home/End jump to start/end
  describe('Home/End — jump to start/end', () => {
    it('Home jumps to start', () => {
      const video = createMockVideo({ currentTime: 30, duration: 60 })
      renderWithVideo(video)
      fireKey('Home')
      expect(video.currentTime).toBe(0)
    })

    it('End jumps to end', () => {
      const video = createMockVideo({ currentTime: 10, duration: 60 })
      renderWithVideo(video)
      fireKey('End')
      expect(video.currentTime).toBe(60)
    })
  })

  // FR-007: Shortcuts scoped — inactive when typing in inputs
  describe('focus scoping', () => {
    it('ignores shortcuts when target is an input element', () => {
      const video = createMockVideo({ paused: true })
      renderWithVideo(video)

      const input = document.createElement('input')
      document.body.appendChild(input)
      const event = new KeyboardEvent('keydown', {
        key: ' ',
        bubbles: true,
      })
      Object.defineProperty(event, 'target', { value: input })
      document.dispatchEvent(event)

      expect(video.play).not.toHaveBeenCalled()
      document.body.removeChild(input)
    })

    it('ignores shortcuts when target is a textarea', () => {
      const video = createMockVideo({ paused: true })
      renderWithVideo(video)

      const textarea = document.createElement('textarea')
      document.body.appendChild(textarea)
      const event = new KeyboardEvent('keydown', {
        key: ' ',
        bubbles: true,
      })
      Object.defineProperty(event, 'target', { value: textarea })
      document.dispatchEvent(event)

      expect(video.play).not.toHaveBeenCalled()
      document.body.removeChild(textarea)
    })
  })

  // NFR-001: No conflict — does nothing when video ref is null
  it('does nothing when videoRef is null', () => {
    const ref = { current: null }
    renderHook(() =>
      useTheaterShortcuts({
        videoRef: ref,
        onExit: onExit as () => void,
        onToggleFullscreen: onToggleFullscreen as () => void,
        enabled: true,
      }),
    )
    fireKey(' ')
    expect(onExit).not.toHaveBeenCalled()
  })

  // FR-007 / NFR-001: Shortcuts inactive when not enabled (not in fullscreen)
  it('does not register shortcuts when enabled is false', () => {
    const video = createMockVideo({ paused: true })
    renderWithVideo(video, false)
    fireKey(' ')
    expect(video.play).not.toHaveBeenCalled()
  })

  // Cleanup
  it('removes keydown listener on unmount', () => {
    const removeSpy = vi.spyOn(document, 'removeEventListener')
    const video = createMockVideo()
    const { unmount } = renderWithVideo(video)

    unmount()

    expect(removeSpy).toHaveBeenCalledWith('keydown', expect.any(Function))
  })
})
