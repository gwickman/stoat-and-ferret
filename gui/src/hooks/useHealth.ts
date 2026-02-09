import { useEffect, useState } from 'react'

export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy'

interface HealthCheck {
  status: string
  [key: string]: unknown
}

interface HealthResponse {
  status: string
  checks: Record<string, HealthCheck>
}

export interface HealthState {
  status: HealthStatus
  checks: Record<string, HealthCheck>
}

function mapStatus(response: HealthResponse): HealthStatus {
  if (response.status === 'ok') return 'healthy'
  if (response.status === 'degraded') return 'degraded'
  return 'unhealthy'
}

export function useHealth(intervalMs = 30_000): HealthState {
  const [state, setState] = useState<HealthState>({
    status: 'unhealthy',
    checks: {},
  })

  useEffect(() => {
    let active = true

    async function poll() {
      try {
        const res = await fetch('/health/ready')
        const data: HealthResponse = await res.json()
        if (active) {
          setState({ status: mapStatus(data), checks: data.checks })
        }
      } catch {
        if (active) {
          setState({ status: 'unhealthy', checks: {} })
        }
      }
    }

    poll()
    const id = setInterval(poll, intervalMs)

    return () => {
      active = false
      clearInterval(id)
    }
  }, [intervalMs])

  return state
}
