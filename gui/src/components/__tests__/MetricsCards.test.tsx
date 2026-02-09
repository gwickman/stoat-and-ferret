import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import MetricsCards from '../MetricsCards'
import type { Metrics } from '../../hooks/useMetrics'

describe('MetricsCards', () => {
  it('displays request count', () => {
    const metrics: Metrics = { requestCount: 42, avgDurationMs: 5.3 }

    render(<MetricsCards metrics={metrics} />)

    expect(screen.getByTestId('metric-request-count')).toBeDefined()
    expect(screen.getByText('42')).toBeDefined()
  })

  it('displays average response time', () => {
    const metrics: Metrics = { requestCount: 10, avgDurationMs: 12.567 }

    render(<MetricsCards metrics={metrics} />)

    expect(screen.getByTestId('metric-avg-duration')).toBeDefined()
    expect(screen.getByText('12.6 ms')).toBeDefined()
  })

  it('shows placeholder when no duration data', () => {
    const metrics: Metrics = { requestCount: 0, avgDurationMs: null }

    render(<MetricsCards metrics={metrics} />)

    expect(screen.getByText('--')).toBeDefined()
  })
})
