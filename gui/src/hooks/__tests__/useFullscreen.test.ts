import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useFullscreen } from '../useFullscreen'
import { useTheaterStore } from '../../stores/theaterStore'

beforeEach(() => {
  vi.restoreAllMocks()
  useTheaterStore.getState().reset()
  // Reset fullscreenElement to null
  Object.defineProperty(document, 'fullscreenElement', {
    value: null,
    writable: true,
    configurable: true,
  })
})

describe('useFullscreen', () => {
  it('calls requestFullscreen on enter', async () => {
    const mockEl = document.createElement('div')
    mockEl.requestFullscreen = vi.fn().mockResolvedValue(undefined)
    const ref = { current: mockEl }

    const { result } = renderHook(() => useFullscreen(ref))

    await act(async () => {
      await result.current.enter()
    })

    expect(mockEl.requestFullscreen).toHaveBeenCalled()
  })

  it('does not call requestFullscreen when already fullscreen', async () => {
    const mockEl = document.createElement('div')
    mockEl.requestFullscreen = vi.fn().mockResolvedValue(undefined)
    const ref = { current: mockEl }

    Object.defineProperty(document, 'fullscreenElement', {
      value: mockEl,
      writable: true,
      configurable: true,
    })

    const { result } = renderHook(() => useFullscreen(ref))

    await act(async () => {
      await result.current.enter()
    })

    expect(mockEl.requestFullscreen).not.toHaveBeenCalled()
  })

  it('calls document.exitFullscreen on exit', async () => {
    const mockEl = document.createElement('div')
    Object.defineProperty(document, 'fullscreenElement', {
      value: mockEl,
      writable: true,
      configurable: true,
    })
    document.exitFullscreen = vi.fn().mockResolvedValue(undefined)
    const ref = { current: mockEl }

    const { result } = renderHook(() => useFullscreen(ref))

    await act(async () => {
      await result.current.exit()
    })

    expect(document.exitFullscreen).toHaveBeenCalled()
  })

  it('does not call exitFullscreen when not fullscreen', async () => {
    document.exitFullscreen = vi.fn().mockResolvedValue(undefined)
    const ref = { current: document.createElement('div') }

    const { result } = renderHook(() => useFullscreen(ref))

    await act(async () => {
      await result.current.exit()
    })

    expect(document.exitFullscreen).not.toHaveBeenCalled()
  })

  it('updates theater store on fullscreenchange — entering', () => {
    const ref = { current: document.createElement('div') }
    renderHook(() => useFullscreen(ref))

    // Simulate entering fullscreen
    Object.defineProperty(document, 'fullscreenElement', {
      value: ref.current,
      writable: true,
      configurable: true,
    })

    act(() => {
      document.dispatchEvent(new Event('fullscreenchange'))
    })

    expect(useTheaterStore.getState().isFullscreen).toBe(true)
  })

  it('updates theater store on fullscreenchange — exiting', () => {
    useTheaterStore.getState().enterTheater()
    const ref = { current: document.createElement('div') }
    renderHook(() => useFullscreen(ref))

    // Simulate exiting fullscreen
    Object.defineProperty(document, 'fullscreenElement', {
      value: null,
      writable: true,
      configurable: true,
    })

    act(() => {
      document.dispatchEvent(new Event('fullscreenchange'))
    })

    expect(useTheaterStore.getState().isFullscreen).toBe(false)
  })

  it('cleans up fullscreenchange listener on unmount', () => {
    const ref = { current: document.createElement('div') }
    const addSpy = vi.spyOn(document, 'addEventListener')
    const removeSpy = vi.spyOn(document, 'removeEventListener')

    const { unmount } = renderHook(() => useFullscreen(ref))

    expect(addSpy).toHaveBeenCalledWith('fullscreenchange', expect.any(Function))

    unmount()

    expect(removeSpy).toHaveBeenCalledWith('fullscreenchange', expect.any(Function))
  })
})
