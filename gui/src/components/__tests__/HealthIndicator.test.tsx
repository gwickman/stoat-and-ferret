import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import HealthIndicator from '../HealthIndicator'

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('HealthIndicator', () => {
  it('shows green when all checks pass', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          status: 'ok',
          checks: { database: { status: 'ok' }, ffmpeg: { status: 'ok' } },
        }),
        { status: 200 },
      ),
    )

    render(<HealthIndicator />)

    await waitFor(() => {
      const dot = screen.getByTestId('health-dot')
      expect(dot.dataset.status).toBe('healthy')
    })
    expect(screen.getByText('Healthy')).toBeDefined()
  })

  it('shows yellow when status is degraded', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          status: 'degraded',
          checks: {
            database: { status: 'ok' },
            ffmpeg: { status: 'error', error: 'not found' },
          },
        }),
        { status: 503 },
      ),
    )

    render(<HealthIndicator />)

    await waitFor(() => {
      const dot = screen.getByTestId('health-dot')
      expect(dot.dataset.status).toBe('degraded')
    })
    expect(screen.getByText('Degraded')).toBeDefined()
  })

  it('shows red when fetch fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Network error'))

    render(<HealthIndicator />)

    await waitFor(() => {
      const dot = screen.getByTestId('health-dot')
      expect(dot.dataset.status).toBe('unhealthy')
    })
    expect(screen.getByText('Unhealthy')).toBeDefined()
  })
})
