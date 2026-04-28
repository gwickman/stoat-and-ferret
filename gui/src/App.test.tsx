import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import App from './App'

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

describe('App', () => {
  it('renders the shell layout', () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('status-bar')).toBeDefined()
  })

  it('renders dashboard page at root', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeDefined()
  })

  it('renders library page at /library', () => {
    render(
      <MemoryRouter initialEntries={['/library']}>
        <App />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: 'Library' })).toBeDefined()
  })

  it('renders projects page at /projects', () => {
    render(
      <MemoryRouter initialEntries={['/projects']}>
        <App />
      </MemoryRouter>,
    )
    expect(screen.getByRole('heading', { name: 'Projects' })).toBeDefined()
  })
})
