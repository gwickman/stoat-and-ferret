import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import StatusBadge from '../StatusBadge'

describe('StatusBadge', () => {
  it.each([
    ['queued', 'bg-blue-500', 'Queued'],
    ['running', 'bg-yellow-500', 'Rendering'],
    ['completed', 'bg-green-500', 'Completed'],
    ['failed', 'bg-red-500', 'Failed'],
    ['cancelled', 'bg-gray-500', 'Cancelled'],
    ['unknown_state', 'bg-gray-500', 'unknown_state'],
  ])('renders %s status with correct dot colour and label', (status, colorClass, label) => {
    render(<StatusBadge status={status} />)
    const dot = screen.getByTestId('status-badge-dot')
    expect(dot.className).toContain(colorClass)
    expect(screen.getByTestId('status-badge-label').textContent).toBe(label)
  })
})
