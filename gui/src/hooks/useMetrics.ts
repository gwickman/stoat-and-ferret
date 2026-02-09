import { useEffect, useState } from 'react'

export interface Metrics {
  requestCount: number
  avgDurationMs: number | null
}

/**
 * Parse Prometheus text format to extract key metrics.
 *
 * Sums all `http_requests_total` samples and computes average duration
 * from `http_request_duration_seconds_sum` / `http_request_duration_seconds_count`.
 */
export function parsePrometheus(text: string): Metrics {
  let requestCount = 0
  let durationSum = 0
  let durationCount = 0

  for (const line of text.split('\n')) {
    if (line.startsWith('#') || line.trim() === '') continue

    if (line.startsWith('http_requests_total')) {
      const value = parseFloat(line.split(/\s+/).pop() ?? '0')
      if (!isNaN(value)) requestCount += value
    } else if (line.startsWith('http_request_duration_seconds_sum')) {
      const value = parseFloat(line.split(/\s+/).pop() ?? '0')
      if (!isNaN(value)) durationSum += value
    } else if (line.startsWith('http_request_duration_seconds_count')) {
      const value = parseFloat(line.split(/\s+/).pop() ?? '0')
      if (!isNaN(value)) durationCount += value
    }
  }

  const avgDurationMs =
    durationCount > 0 ? (durationSum / durationCount) * 1000 : null

  return { requestCount, avgDurationMs }
}

export function useMetrics(intervalMs = 30_000): Metrics {
  const [metrics, setMetrics] = useState<Metrics>({
    requestCount: 0,
    avgDurationMs: null,
  })

  useEffect(() => {
    let active = true

    async function poll() {
      try {
        const res = await fetch('/metrics')
        const text = await res.text()
        if (active) {
          setMetrics(parsePrometheus(text))
        }
      } catch {
        // Keep last known metrics on error
      }
    }

    poll()
    const id = setInterval(poll, intervalMs)

    return () => {
      active = false
      clearInterval(id)
    }
  }, [intervalMs])

  return metrics
}
