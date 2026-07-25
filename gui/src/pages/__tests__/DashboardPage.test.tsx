import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import DashboardPage from '../DashboardPage'

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
    new Response(JSON.stringify({}), { status: 200 }),
  )
})

function renderPage() {
  return render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>,
  )
}

describe('DashboardPage', () => {
  it('renders with id="main-content" and skip-link target', () => {
    renderPage()
    const main = screen.getByTestId('dashboard-page')
    expect(main).toHaveAttribute('id', 'main-content')
    expect(main).toHaveAttribute('data-testid', 'dashboard-page')
    expect(screen.queryAllByRole('main')).toHaveLength(0)
  })

  it('renders dashboard heading', () => {
    renderPage()
    expect(screen.getByText('Dashboard')).toBeDefined()
  })
})
