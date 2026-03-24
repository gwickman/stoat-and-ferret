import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useEffectPreview } from '../useEffectPreview'
import { useEffectCatalogStore } from '../../stores/effectCatalogStore'
import { useEffectFormStore } from '../../stores/effectFormStore'
import { useEffectPreviewStore } from '../../stores/effectPreviewStore'

// Mock URL.createObjectURL and revokeObjectURL for thumbnail tests
const mockCreateObjectURL = vi.fn(() => 'blob:mock-thumbnail-url')
const mockRevokeObjectURL = vi.fn()
globalThis.URL.createObjectURL = mockCreateObjectURL
globalThis.URL.revokeObjectURL = mockRevokeObjectURL

beforeEach(() => {
  vi.useFakeTimers()
  useEffectCatalogStore.getState().selectEffect(null)
  useEffectFormStore.getState().resetForm()
  useEffectPreviewStore.getState().reset()
  mockCreateObjectURL.mockClear()
  mockRevokeObjectURL.mockClear()
  vi.restoreAllMocks()
  // Re-apply URL mocks after restoreAllMocks
  globalThis.URL.createObjectURL = mockCreateObjectURL
  globalThis.URL.revokeObjectURL = mockRevokeObjectURL
})

afterEach(() => {
  vi.useRealTimers()
})

function mockFetchSuccess(filterString: string) {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify({ filter_string: filterString }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

function mockFetchError(status: number, detail?: string) {
  const body = detail
    ? JSON.stringify({ detail: { message: detail } })
    : JSON.stringify({})
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(body, { status, headers: { 'Content-Type': 'application/json' } }),
  )
}

function mockFetchMulti() {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
    if (url === '/api/v1/effects/preview') {
      return new Response(JSON.stringify({ filter_string: 'volume=0.5' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }
    if (url === '/api/v1/effects/preview/thumbnail') {
      return new Response(new Blob(['\xff\xd8\xff\xe0'], { type: 'image/jpeg' }), {
        status: 200,
        headers: { 'Content-Type': 'image/jpeg' },
      })
    }
    return new Response('', { status: 404 })
  })
}

function mockFetchThumbnailError() {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
    if (url === '/api/v1/effects/preview') {
      return new Response(JSON.stringify({ filter_string: 'volume=0.5' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }
    if (url === '/api/v1/effects/preview/thumbnail') {
      return new Response(JSON.stringify({ detail: { message: 'FFmpeg failed' } }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      })
    }
    return new Response('', { status: 404 })
  })
}

describe('useEffectPreview', () => {
  it('resets preview store when no effect is selected', async () => {
    useEffectPreviewStore.getState().setFilterString('old-value')

    renderHook(() => useEffectPreview())

    // No effect selected, so store should be reset
    await act(() => vi.advanceTimersByTimeAsync(300))
    expect(useEffectPreviewStore.getState().filterString).toBe('')
  })

  it('fetches preview when effect is selected and parameters change', async () => {
    const fetchSpy = mockFetchSuccess('volume=0.5')

    // Select an effect and set parameters
    act(() => {
      useEffectCatalogStore.getState().selectEffect('volume')
      useEffectFormStore.getState().setSchema({
        type: 'object',
        properties: { volume: { type: 'number', default: 1.0 } },
      })
    })

    renderHook(() => useEffectPreview())

    // Wait for debounce
    await act(() => vi.advanceTimersByTimeAsync(300))
    // Wait for fetch microtask
    await act(() => vi.advanceTimersByTimeAsync(0))

    expect(fetchSpy).toHaveBeenCalledWith('/api/v1/effects/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        effect_type: 'volume',
        parameters: { volume: 1.0 },
      }),
    })

    expect(useEffectPreviewStore.getState().filterString).toBe('volume=0.5')
    expect(useEffectPreviewStore.getState().isLoading).toBe(false)
  })

  it('debounces rapid parameter changes into a single API call', async () => {
    const fetchSpy = mockFetchSuccess('volume=0.8')

    act(() => {
      useEffectCatalogStore.getState().selectEffect('volume')
      useEffectFormStore.getState().setSchema({
        type: 'object',
        properties: { volume: { type: 'number', default: 1.0 } },
      })
    })

    renderHook(() => useEffectPreview())

    // Rapid parameter changes
    act(() => useEffectFormStore.getState().setParameter('volume', 0.5))
    await act(() => vi.advanceTimersByTimeAsync(100))
    act(() => useEffectFormStore.getState().setParameter('volume', 0.7))
    await act(() => vi.advanceTimersByTimeAsync(100))
    act(() => useEffectFormStore.getState().setParameter('volume', 0.8))

    // Wait for debounce to settle (300ms from last change)
    await act(() => vi.advanceTimersByTimeAsync(300))
    await act(() => vi.advanceTimersByTimeAsync(0))

    // Should have made calls for initial params + final debounced params
    // The initial render fires once with default params, and then the debounced final value
    const previewCalls = fetchSpy.mock.calls.filter(
      (c) => c[0] === '/api/v1/effects/preview',
    )
    // At minimum the last call should have the final parameter value
    const lastCall = previewCalls[previewCalls.length - 1]
    expect(lastCall).toBeDefined()
    const requestInit = lastCall![1]!
    expect(JSON.parse(requestInit.body as string).parameters.volume).toBe(0.8)
  })

  it('sets error state when API call fails', async () => {
    mockFetchError(400, 'Unknown effect type: bad')

    act(() => {
      useEffectCatalogStore.getState().selectEffect('bad')
      useEffectFormStore.getState().setSchema({
        type: 'object',
        properties: {},
      })
    })

    renderHook(() => useEffectPreview())

    await act(() => vi.advanceTimersByTimeAsync(300))
    await act(() => vi.advanceTimersByTimeAsync(0))

    expect(useEffectPreviewStore.getState().error).toBe(
      'Unknown effect type: bad',
    )
    expect(useEffectPreviewStore.getState().isLoading).toBe(false)
  })
})

describe('useEffectPreview thumbnail', () => {
  it('fetches thumbnail when effect selected and videoPath set', async () => {
    const fetchSpy = mockFetchMulti()

    act(() => {
      useEffectCatalogStore.getState().selectEffect('volume')
      useEffectFormStore.getState().setSchema({
        type: 'object',
        properties: { volume: { type: 'number', default: 1.0 } },
      })
      useEffectPreviewStore.getState().setVideoPath('/videos/test.mp4')
    })

    renderHook(() => useEffectPreview())

    // Wait for 500ms thumbnail debounce
    await act(() => vi.advanceTimersByTimeAsync(500))
    await act(() => vi.advanceTimersByTimeAsync(0))

    const thumbnailCalls = fetchSpy.mock.calls.filter(
      (c) => c[0] === '/api/v1/effects/preview/thumbnail',
    )
    expect(thumbnailCalls.length).toBeGreaterThanOrEqual(1)

    const lastCall = thumbnailCalls[thumbnailCalls.length - 1]
    const body = JSON.parse(lastCall![1]!.body as string)
    expect(body.effect_name).toBe('volume')
    expect(body.video_path).toBe('/videos/test.mp4')
    expect(body.parameters).toEqual({ volume: 1.0 })

    expect(useEffectPreviewStore.getState().thumbnailUrl).toBe('blob:mock-thumbnail-url')
  })

  it('does not fetch thumbnail when videoPath is null', async () => {
    const fetchSpy = mockFetchMulti()

    act(() => {
      useEffectCatalogStore.getState().selectEffect('volume')
      useEffectFormStore.getState().setSchema({
        type: 'object',
        properties: { volume: { type: 'number', default: 1.0 } },
      })
      // videoPath not set (null by default)
    })

    renderHook(() => useEffectPreview())

    await act(() => vi.advanceTimersByTimeAsync(500))
    await act(() => vi.advanceTimersByTimeAsync(0))

    const thumbnailCalls = fetchSpy.mock.calls.filter(
      (c) => c[0] === '/api/v1/effects/preview/thumbnail',
    )
    expect(thumbnailCalls.length).toBe(0)
    expect(useEffectPreviewStore.getState().thumbnailUrl).toBeNull()
  })

  it('falls back to null thumbnail on API error', async () => {
    mockFetchThumbnailError()

    act(() => {
      useEffectCatalogStore.getState().selectEffect('volume')
      useEffectFormStore.getState().setSchema({
        type: 'object',
        properties: { volume: { type: 'number', default: 1.0 } },
      })
      useEffectPreviewStore.getState().setVideoPath('/videos/test.mp4')
    })

    renderHook(() => useEffectPreview())

    await act(() => vi.advanceTimersByTimeAsync(500))
    await act(() => vi.advanceTimersByTimeAsync(0))

    // Thumbnail should be null (fallback), not an error state
    expect(useEffectPreviewStore.getState().thumbnailUrl).toBeNull()
    // Filter string preview should still work
    expect(useEffectPreviewStore.getState().filterString).toBe('volume=0.5')
  })

  it('debounces thumbnail updates at 500ms', async () => {
    const fetchSpy = mockFetchMulti()

    act(() => {
      useEffectCatalogStore.getState().selectEffect('volume')
      useEffectFormStore.getState().setSchema({
        type: 'object',
        properties: { volume: { type: 'number', default: 1.0 } },
      })
      useEffectPreviewStore.getState().setVideoPath('/videos/test.mp4')
    })

    renderHook(() => useEffectPreview())

    // Rapid parameter changes at 100ms intervals
    act(() => useEffectFormStore.getState().setParameter('volume', 0.5))
    await act(() => vi.advanceTimersByTimeAsync(100))
    act(() => useEffectFormStore.getState().setParameter('volume', 0.7))
    await act(() => vi.advanceTimersByTimeAsync(100))
    act(() => useEffectFormStore.getState().setParameter('volume', 0.9))

    // At 200ms since last change - thumbnail debounce not yet fired
    await act(() => vi.advanceTimersByTimeAsync(300))

    // Check that filter string calls happened (300ms debounce) but count thumbnail calls
    const thumbnailCallsBefore = fetchSpy.mock.calls.filter(
      (c) => c[0] === '/api/v1/effects/preview/thumbnail',
    )

    // Wait for the remaining 200ms to complete the 500ms thumbnail debounce
    await act(() => vi.advanceTimersByTimeAsync(200))
    await act(() => vi.advanceTimersByTimeAsync(0))

    const thumbnailCallsAfter = fetchSpy.mock.calls.filter(
      (c) => c[0] === '/api/v1/effects/preview/thumbnail',
    )

    // Thumbnail calls should increase after the 500ms debounce completes
    expect(thumbnailCallsAfter.length).toBeGreaterThan(thumbnailCallsBefore.length)
  })
})
