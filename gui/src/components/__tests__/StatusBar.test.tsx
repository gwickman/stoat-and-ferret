import { act, render, screen, waitFor } from '@testing-library/react'
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

const FALLBACK = 'https://github.com/gwickman/stoat-and-ferret'

async function renderWithSourceUrl(sourceUrl: unknown): Promise<HTMLElement> {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(
      JSON.stringify({ source_url: sourceUrl, version: '0.84.0', commit: 'abc', license: 'AGPL-3.0' }),
      { status: 200 }
    )
  )
  render(<StatusBar connectionState="connected" />)
  await act(async () => {})
  return screen.getByTestId('source-code-link')
}

describe('StatusBar URL scheme validation', () => {
  it('rejects javascript: scheme', async () => {
    const link = await renderWithSourceUrl('javascript:alert(1)')
    expect(link.getAttribute('href')).toBe(FALLBACK)
  })

  it('rejects data: scheme', async () => {
    const link = await renderWithSourceUrl('data:text/html,x')
    expect(link.getAttribute('href')).toBe(FALLBACK)
  })

  it('rejects relative path', async () => {
    const link = await renderWithSourceUrl('/relative/path')
    expect(link.getAttribute('href')).toBe(FALLBACK)
  })

  it('rejects protocol-relative URL', async () => {
    const link = await renderWithSourceUrl('//host/path')
    expect(link.getAttribute('href')).toBe(FALLBACK)
  })

  it('rejects empty string', async () => {
    const link = await renderWithSourceUrl('')
    expect(link.getAttribute('href')).toBe(FALLBACK)
  })

  it('accepts valid https URL', async () => {
    const url = 'https://github.com/gwickman/stoat-and-ferret'
    const link = await renderWithSourceUrl(url)
    expect(link.getAttribute('href')).toBe(url)
  })

  it('accepts valid http URL', async () => {
    const url = 'http://internal.host/source'
    const link = await renderWithSourceUrl(url)
    expect(link.getAttribute('href')).toBe(url)
  })
})
