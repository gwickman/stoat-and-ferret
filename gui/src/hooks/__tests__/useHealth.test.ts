import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useHealth } from '../useHealth'

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('useHealth', () => {
  it('returns healthy when all checks pass', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          status: 'ok',
          checks: { database: { status: 'ok' } },
        }),
        { status: 200 },
      ),
    )

    const { result } = renderHook(() => useHealth(30_000))

    await waitFor(() => {
      expect(result.current.status).toBe('healthy')
    })
  })

  it('returns degraded when status is degraded', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          status: 'degraded',
          checks: { ffmpeg: { status: 'error' } },
        }),
        { status: 503 },
      ),
    )

    const { result } = renderHook(() => useHealth(30_000))

    await waitFor(() => {
      expect(result.current.status).toBe('degraded')
    })
  })

  it('returns unhealthy when fetch fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useHealth(30_000))

    await waitFor(() => {
      expect(result.current.status).toBe('unhealthy')
    })
  })

  it('polls at the configured interval', async () => {
    vi.useFakeTimers()
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({ status: 'ok', checks: {} }),
        { status: 200 },
      ),
    )

    const { result } = renderHook(() => useHealth(5_000))

    // Flush the initial poll (microtask)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    expect(fetchSpy).toHaveBeenCalledTimes(1)
    expect(result.current.status).toBe('healthy')

    // Advance timer to trigger second poll
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000)
    })
    expect(fetchSpy).toHaveBeenCalledTimes(2)

    vi.useRealTimers()
  })
})
