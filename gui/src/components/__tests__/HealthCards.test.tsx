import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import HealthCards from '../HealthCards'
import type { HealthState } from '../../hooks/useHealth'

describe('HealthCards', () => {
  it('renders green cards when all checks pass', () => {
    const health: HealthState = {
      status: 'healthy',
      checks: {
        database: { status: 'ok', latency_ms: 1.5 },
        ffmpeg: { status: 'ok', version: '6.0' },
      },
    }

    render(<HealthCards health={health} />)

    const apiCard = screen.getByTestId('health-card-Python API')
    expect(apiCard).toBeDefined()
    expect(screen.getByTestId('health-dot-Python API').dataset.status).toBe(
      'ok',
    )

    const ffmpegCard = screen.getByTestId('health-card-FFmpeg')
    expect(ffmpegCard).toBeDefined()
    expect(screen.getByTestId('health-dot-FFmpeg').dataset.status).toBe('ok')

    const rustCard = screen.getByTestId('health-card-Rust Core')
    expect(rustCard).toBeDefined()
    expect(screen.getByTestId('health-dot-Rust Core').dataset.status).toBe(
      'ok',
    )
  })

  it('renders red card for failed component', () => {
    const health: HealthState = {
      status: 'degraded',
      checks: {
        database: { status: 'ok' },
        ffmpeg: { status: 'error', error: 'not found' },
      },
    }

    render(<HealthCards health={health} />)

    expect(screen.getByTestId('health-dot-Python API').dataset.status).toBe(
      'ok',
    )
    expect(screen.getByTestId('health-dot-FFmpeg').dataset.status).toBe(
      'error',
    )
  })

  it('renders red Rust Core card when overall status is unhealthy', () => {
    const health: HealthState = {
      status: 'unhealthy',
      checks: {},
    }

    render(<HealthCards health={health} />)

    expect(screen.getByTestId('health-dot-Rust Core').dataset.status).toBe(
      'error',
    )
  })

  it('renders unknown status when check is missing', () => {
    const health: HealthState = {
      status: 'healthy',
      checks: {},
    }

    render(<HealthCards health={health} />)

    expect(screen.getByTestId('health-dot-Python API').dataset.status).toBe(
      'unknown',
    )
  })
})
