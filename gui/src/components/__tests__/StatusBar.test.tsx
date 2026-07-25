import { act, render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import StatusBar from '../StatusBar'

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('StatusBar', () => {
  const INFO = JSON.stringify({ source_url: 'https://github.com/gwickman/stoat-and-ferret', version: '0.1.0', commit: 'unknown', license: 'AGPL-3.0-or-later' })

  it.each([
    ['connected', 'WebSocket: Connected'],
    ['disconnected', 'WebSocket: Disconnected'],
    ['reconnecting', 'WebSocket: Reconnecting...'],
  ] as const)('shows %s state', (connectionState, expectedText) => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(INFO, { status: 200 })
    )
    render(<StatusBar connectionState={connectionState} />)
    expect(screen.getByText(expectedText)).toBeDefined()
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
  const HTTPS_URL = 'https://github.com/gwickman/stoat-and-ferret'
  const HTTP_URL = 'http://internal.host/source'

  it.each([
    ['javascript: scheme', 'javascript:alert(1)', FALLBACK],
    ['data: scheme', 'data:text/html,x', FALLBACK],
    ['relative path', '/relative/path', FALLBACK],
    ['protocol-relative URL', '//host/path', FALLBACK],
    ['empty string', '', FALLBACK],
    ['valid https URL', HTTPS_URL, HTTPS_URL],
    ['valid http URL', HTTP_URL, HTTP_URL],
  ])('handles %s', async (_label, input, expectedHref) => {
    const link = await renderWithSourceUrl(input)
    expect(link.getAttribute('href')).toBe(expectedHref)
  })
})
