import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ProxyStatusBadge from '../ProxyStatusBadge'

let mockLastMessage: MessageEvent | null = null

vi.mock('../../../hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    state: 'connected' as const,
    send: vi.fn(),
    lastMessage: mockLastMessage,
  }),
}))

describe('ProxyStatusBadge', () => {
  beforeEach(() => {
    mockLastMessage = null
  })

  it('renders green badge for ready status', () => {
    render(<ProxyStatusBadge videoId="v1" proxyStatus="ready" />)
    const badge = screen.getByTestId('proxy-status-badge')
    expect(badge).toBeTruthy()
    expect(badge.dataset.status).toBe('ready')
    expect(badge.className).toContain('bg-green-500')
  })

  it('renders yellow badge for generating status', () => {
    render(<ProxyStatusBadge videoId="v1" proxyStatus="generating" />)
    const badge = screen.getByTestId('proxy-status-badge')
    expect(badge.dataset.status).toBe('generating')
    expect(badge.className).toContain('bg-yellow-500')
  })

  it('renders gray badge for none status', () => {
    render(<ProxyStatusBadge videoId="v1" proxyStatus="none" />)
    const badge = screen.getByTestId('proxy-status-badge')
    expect(badge.dataset.status).toBe('none')
    expect(badge.className).toContain('bg-gray-500')
  })

  it('defaults to none when no proxyStatus provided', () => {
    render(<ProxyStatusBadge videoId="v1" />)
    const badge = screen.getByTestId('proxy-status-badge')
    expect(badge.dataset.status).toBe('none')
    expect(badge.className).toContain('bg-gray-500')
  })

  it('updates to ready on PROXY_READY WebSocket event', async () => {
    mockLastMessage = new MessageEvent('message', {
      data: JSON.stringify({
        type: 'proxy.ready',
        payload: { video_id: 'v1', quality: 'high' },
      }),
    })
    render(<ProxyStatusBadge videoId="v1" proxyStatus="generating" />)
    await waitFor(() => {
      expect(screen.getByTestId('proxy-status-badge').dataset.status).toBe('ready')
    })
  })

  it('ignores PROXY_READY events for other videos', () => {
    mockLastMessage = new MessageEvent('message', {
      data: JSON.stringify({
        type: 'proxy.ready',
        payload: { video_id: 'v2', quality: 'high' },
      }),
    })
    render(<ProxyStatusBadge videoId="v1" proxyStatus="generating" />)
    const badge = screen.getByTestId('proxy-status-badge')
    expect(badge.dataset.status).toBe('generating')
  })

  it('is visible on the page', () => {
    render(<ProxyStatusBadge videoId="v1" />)
    expect(screen.getByTestId('proxy-status-badge')).toBeTruthy()
  })
})
