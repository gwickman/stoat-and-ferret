import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import StatusBadge from '../StatusBadge'

describe('StatusBadge', () => {
  it('renders blue dot for "queued"', () => {
    render(<StatusBadge status="queued" />)
    const dot = screen.getByTestId('status-badge-dot')
    expect(dot.className).toContain('bg-blue-500')
    expect(screen.getByTestId('status-badge-label').textContent).toBe('Queued')
  })

  it('renders yellow dot for "running" with label "Rendering"', () => {
    render(<StatusBadge status="running" />)
    const dot = screen.getByTestId('status-badge-dot')
    expect(dot.className).toContain('bg-yellow-500')
    expect(screen.getByTestId('status-badge-label').textContent).toBe('Rendering')
  })

  it('renders green dot for "completed"', () => {
    render(<StatusBadge status="completed" />)
    const dot = screen.getByTestId('status-badge-dot')
    expect(dot.className).toContain('bg-green-500')
    expect(screen.getByTestId('status-badge-label').textContent).toBe('Completed')
  })

  it('renders red dot for "failed"', () => {
    render(<StatusBadge status="failed" />)
    const dot = screen.getByTestId('status-badge-dot')
    expect(dot.className).toContain('bg-red-500')
    expect(screen.getByTestId('status-badge-label').textContent).toBe('Failed')
  })

  it('renders gray dot for "cancelled"', () => {
    render(<StatusBadge status="cancelled" />)
    const dot = screen.getByTestId('status-badge-dot')
    expect(dot.className).toContain('bg-gray-500')
    expect(screen.getByTestId('status-badge-label').textContent).toBe('Cancelled')
  })

  it('renders gray fallback for unknown status', () => {
    render(<StatusBadge status="unknown_state" />)
    const dot = screen.getByTestId('status-badge-dot')
    expect(dot.className).toContain('bg-gray-500')
    expect(screen.getByTestId('status-badge-label').textContent).toBe('unknown_state')
  })
})
