import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  useTimelineSync,
  SYNC_DEBOUNCE_MS,
  SYNC_THRESHOLD_S,
} from '../useTimelineSync'
import { usePreviewStore } from '../../stores/previewStore'
import { useTimelineStore } from '../../stores/timelineStore'

function createMockVideo(
  overrides: Partial<HTMLVideoElement> = {},
): HTMLVideoElement {
  return {
    currentTime: 0,
    duration: 60,
    paused: true,
    ...overrides,
  } as unknown as HTMLVideoElement
}

describe('useTimelineSync', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    usePreviewStore.getState().reset()
    useTimelineStore.getState().reset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('syncs player position to timeline playhead after debounce', () => {
    const ref = { current: createMockVideo() }
    renderHook(() => useTimelineSync(ref))

    act(() => {
      usePreviewStore.setState({ position: 5.0 })
    })

    // Before debounce fires, playhead unchanged
    expect(useTimelineStore.getState().playheadPosition).toBe(0)

    act(() => {
      vi.advanceTimersByTime(SYNC_DEBOUNCE_MS)
    })

    expect(useTimelineStore.getState().playheadPosition).toBe(5.0)
  })

  it('does not sync when difference is below threshold', () => {
    const ref = { current: createMockVideo() }

    useTimelineStore.getState().setPlayheadPosition(5.0)
    usePreviewStore.setState({ position: 5.0 + SYNC_THRESHOLD_S * 0.5 })

    renderHook(() => useTimelineSync(ref))

    act(() => {
      vi.advanceTimersByTime(SYNC_DEBOUNCE_MS)
    })

    expect(useTimelineStore.getState().playheadPosition).toBe(5.0)
  })

  it('syncs when difference exceeds threshold', () => {
    const ref = { current: createMockVideo() }

    useTimelineStore.getState().setPlayheadPosition(5.0)

    renderHook(() => useTimelineSync(ref))

    act(() => {
      usePreviewStore.setState({ position: 5.0 + SYNC_THRESHOLD_S + 0.1 })
    })

    act(() => {
      vi.advanceTimersByTime(SYNC_DEBOUNCE_MS)
    })

    expect(useTimelineStore.getState().playheadPosition).toBe(
      5.0 + SYNC_THRESHOLD_S + 0.1,
    )
  })

  it('seeks video on seekFromTimeline call', () => {
    const video = createMockVideo()
    const ref = { current: video }
    usePreviewStore.setState({ duration: 60 })

    const { result } = renderHook(() => useTimelineSync(ref))

    act(() => {
      result.current.seekFromTimeline(10.0)
    })

    expect(video.currentTime).toBe(10.0)
    expect(usePreviewStore.getState().position).toBe(10.0)
    expect(useTimelineStore.getState().playheadPosition).toBe(10.0)
  })

  it('guard flag prevents loop during seek', () => {
    const video = createMockVideo()
    const ref = { current: video }
    usePreviewStore.setState({ duration: 60 })

    const { result } = renderHook(() => useTimelineSync(ref))

    // Seek from timeline — sets guard
    act(() => {
      result.current.seekFromTimeline(10.0)
    })

    // Simulate player firing a position update during seek
    act(() => {
      usePreviewStore.setState({ position: 10.5 })
    })

    act(() => {
      vi.advanceTimersByTime(SYNC_DEBOUNCE_MS)
    })

    // Playhead should stay at 10.0, not be overwritten by 10.5
    expect(useTimelineStore.getState().playheadPosition).toBe(10.0)
  })

  it('resumes sync after guard resets', () => {
    const video = createMockVideo()
    const ref = { current: video }
    usePreviewStore.setState({ duration: 60 })

    const { result } = renderHook(() => useTimelineSync(ref))

    act(() => {
      result.current.seekFromTimeline(10.0)
    })

    // Wait for guard to reset
    act(() => {
      vi.advanceTimersByTime(SYNC_DEBOUNCE_MS)
    })

    // Now a new position change should sync through
    act(() => {
      usePreviewStore.setState({ position: 20.0 })
    })

    act(() => {
      vi.advanceTimersByTime(SYNC_DEBOUNCE_MS)
    })

    expect(useTimelineStore.getState().playheadPosition).toBe(20.0)
  })

  it('debounces rapid position updates', () => {
    const ref = { current: createMockVideo() }
    renderHook(() => useTimelineSync(ref))

    act(() => {
      usePreviewStore.setState({ position: 1.0 })
    })
    act(() => {
      usePreviewStore.setState({ position: 2.0 })
    })
    act(() => {
      usePreviewStore.setState({ position: 3.0 })
    })

    // Before debounce, playhead unchanged
    expect(useTimelineStore.getState().playheadPosition).toBe(0)

    act(() => {
      vi.advanceTimersByTime(SYNC_DEBOUNCE_MS)
    })

    // Only the final value is synced
    expect(useTimelineStore.getState().playheadPosition).toBe(3.0)
  })

  it('does nothing when videoRef is null', () => {
    const ref = { current: null }
    usePreviewStore.setState({ duration: 60 })

    const { result } = renderHook(() => useTimelineSync(ref))

    act(() => {
      result.current.seekFromTimeline(10.0)
    })

    // No crash, stores unchanged
    expect(useTimelineStore.getState().playheadPosition).toBe(0)
  })
})
