import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import StatusBar from '../StatusBar'

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('StatusBar', () => {
  it('shows connected state', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ source_url: 'https://github.com/gwickman/stoat-and-ferret', version: '0.1.0', commit: 'unknown', license: 'AGPL-3.0-or-later' }), { status: 200 })
    )
    render(<StatusBar connectionState="connected" />)
    expect(screen.getByText('WebSocket: Connected')).toBeDefined()
  })

  it('shows disconnected state', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ source_url: 'https://github.com/gwickman/stoat-and-ferret', version: '0.1.0', commit: 'unknown', license: 'AGPL-3.0-or-later' }), { status: 200 })
    )
    render(<StatusBar connectionState="disconnected" />)
    expect(screen.getByText('WebSocket: Disconnected')).toBeDefined()
  })

  it('shows reconnecting state', () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ source_url: 'https://github.com/gwickman/stoat-and-ferret', version: '0.1.0', commit: 'unknown', license: 'AGPL-3.0-or-later' }), { status: 200 })
    )
    render(<StatusBar connectionState="reconnecting" />)
    expect(screen.getByText('WebSocket: Reconnecting...')).toBeDefined()
  })
})

describe('Source compliance link', () => {
  it('renders anchor with data-testid source-code-link when API returns source_url', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({ source_url: 'https://custom.example.com', version: '0.83.0', commit: 'abc123', license: 'AGPL-3.0-or-later' }),
        { status: 200 }
      )
    )
    render(<StatusBar connectionState="connected" />)
    const link = await screen.findByTestId('source-code-link')
    expect(link).toBeDefined()
    expect(link.getAttribute('href')).toBe('https://custom.example.com')
    expect(link.textContent).toBe('Source')
  })

  it('shows fallback link on fetch failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network error'))
    render(<StatusBar connectionState="connected" />)
    await waitFor(() => {
      const link = screen.getByTestId('source-code-link')
      expect(link.getAttribute('href')).toBe('https://github.com/gwickman/stoat-and-ferret')
    })
  })
})
