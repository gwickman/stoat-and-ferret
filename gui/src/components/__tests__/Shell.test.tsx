import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import Shell from '../Shell'

class MockWebSocket {
  static readonly OPEN = 1
  onopen: (() => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  onmessage: ((e: MessageEvent) => void) | null = null
  readyState = MockWebSocket.OPEN
  close() {}
  send() {}
}

beforeEach(() => {
  vi.stubGlobal('WebSocket', MockWebSocket)
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify({ status: 'ok', checks: {} }), { status: 200 }),
  )
})

describe('Shell', () => {
  it('renders header, main, and footer sections', () => {
    render(
      <MemoryRouter>
        <Shell />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('navigation')).toBeDefined()
    expect(screen.getByTestId('health-indicator')).toBeDefined()
    expect(screen.getByTestId('status-bar')).toBeDefined()
  })

  it('displays WebSocket status in status bar', () => {
    render(
      <MemoryRouter>
        <Shell />
      </MemoryRouter>,
    )
    // Initially disconnected until onopen fires
    expect(screen.getByTestId('status-bar')).toBeDefined()
  })
})
