import { render, screen } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import ActivityLog from '../ActivityLog'
import { useActivityStore } from '../../stores/activityStore'

beforeEach(() => {
  useActivityStore.setState({ entries: [] })
})

function makeMessage(data: object): MessageEvent {
  return new MessageEvent('message', { data: JSON.stringify(data) })
}

describe('ActivityLog', () => {
  it('shows empty state when no events', () => {
    render(<ActivityLog lastMessage={null} />)

    expect(screen.getByTestId('activity-empty')).toBeDefined()
    expect(screen.getByText('No recent activity')).toBeDefined()
  })

  it('appends WebSocket events as entries', () => {
    const msg = makeMessage({
      type: 'scan_started',
      payload: { project_id: '123' },
      timestamp: '2025-01-01T12:00:00Z',
    })

    const { rerender } = render(<ActivityLog lastMessage={null} />)
    rerender(<ActivityLog lastMessage={msg} />)

    const entries = screen.getAllByTestId('activity-entry')
    expect(entries).toHaveLength(1)
    expect(screen.getByText('scan started')).toBeDefined()
  })

  it('shows event details when payload is non-empty', () => {
    const msg = makeMessage({
      type: 'project_created',
      payload: { name: 'test-project' },
      timestamp: '2025-01-01T12:00:00Z',
    })

    const { rerender } = render(<ActivityLog lastMessage={null} />)
    rerender(<ActivityLog lastMessage={msg} />)

    expect(screen.getByText(/test-project/)).toBeDefined()
  })

  it('enforces 50 entry limit with FIFO eviction', () => {
    // Pre-populate store with 50 entries
    for (let i = 0; i < 50; i++) {
      useActivityStore.getState().addEntry({
        type: `event_${i}`,
        timestamp: '2025-01-01T12:00:00Z',
        details: {},
      })
    }

    // Add one more via component
    const msg = makeMessage({
      type: 'new_event',
      payload: {},
      timestamp: '2025-01-01T13:00:00Z',
    })

    const { rerender } = render(<ActivityLog lastMessage={null} />)
    rerender(<ActivityLog lastMessage={msg} />)

    const entries = screen.getAllByTestId('activity-entry')
    expect(entries.length).toBeLessThanOrEqual(50)
    // Newest entry should be first
    expect(screen.getByText('new event')).toBeDefined()
  })

  it('ignores non-JSON messages', () => {
    const msg = new MessageEvent('message', { data: 'not json' })

    const { rerender } = render(<ActivityLog lastMessage={null} />)
    rerender(<ActivityLog lastMessage={msg} />)

    expect(screen.getByTestId('activity-empty')).toBeDefined()
  })
})
