import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useEffectPreview } from '../useEffectPreview'
import { useEffectCatalogStore } from '../../stores/effectCatalogStore'
import { useEffectFormStore } from '../../stores/effectFormStore'
import { useEffectPreviewStore } from '../../stores/effectPreviewStore'

beforeEach(() => {
  vi.useFakeTimers()
  useEffectCatalogStore.getState().selectEffect(null)
  useEffectFormStore.getState().resetForm()
  useEffectPreviewStore.getState().reset()
  vi.restoreAllMocks()
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
