import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useMetrics, parsePrometheus } from '../useMetrics'

const SAMPLE_METRICS = `# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",path="/health/live",status="200"} 5.0
http_requests_total{method="GET",path="/api/v1/videos",status="200"} 3.0
# HELP http_request_duration_seconds HTTP request duration in seconds
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.005",method="GET",path="/health/live"} 5.0
http_request_duration_seconds_sum{method="GET",path="/health/live"} 0.01
http_request_duration_seconds_count{method="GET",path="/health/live"} 5.0
http_request_duration_seconds_sum{method="GET",path="/api/v1/videos"} 0.06
http_request_duration_seconds_count{method="GET",path="/api/v1/videos"} 3.0
`

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('parsePrometheus', () => {
  it('sums request count across all labels', () => {
    const result = parsePrometheus(SAMPLE_METRICS)
    expect(result.requestCount).toBe(8)
  })

  it('computes average duration in milliseconds', () => {
    const result = parsePrometheus(SAMPLE_METRICS)
    // Total sum = 0.01 + 0.06 = 0.07, total count = 5 + 3 = 8
    // Avg = 0.07 / 8 * 1000 = 8.75ms
    expect(result.avgDurationMs).toBeCloseTo(8.75)
  })

  it('returns null duration when no data', () => {
    const result = parsePrometheus('')
    expect(result.requestCount).toBe(0)
    expect(result.avgDurationMs).toBeNull()
  })
})

describe('useMetrics', () => {
  it('fetches and parses metrics from /metrics', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(SAMPLE_METRICS, { status: 200 }),
    )

    const { result } = renderHook(() => useMetrics(30_000))

    await waitFor(() => {
      expect(result.current.requestCount).toBe(8)
    })
    expect(result.current.avgDurationMs).toBeCloseTo(8.75)
  })

  it('keeps last metrics on fetch error', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useMetrics(30_000))

    // Should keep defaults without throwing
    await waitFor(() => {
      expect(result.current.requestCount).toBe(0)
    })
  })

  it('polls at the configured interval', async () => {
    vi.useFakeTimers()
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(SAMPLE_METRICS, { status: 200 }),
    )

    const { result } = renderHook(() => useMetrics(5_000))

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0)
    })
    expect(fetchSpy).toHaveBeenCalledTimes(1)
    expect(result.current.requestCount).toBe(8)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000)
    })
    expect(fetchSpy).toHaveBeenCalledTimes(2)

    vi.useRealTimers()
  })
})
