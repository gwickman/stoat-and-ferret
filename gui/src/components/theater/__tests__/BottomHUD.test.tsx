import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import BottomHUD from '../BottomHUD'
import { usePreviewStore } from '../../../stores/previewStore'

let mockLastMessage: MessageEvent | null = null

vi.mock('../../../hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    state: 'connected' as const,
    send: vi.fn(),
    lastMessage: mockLastMessage,
  }),
}))

function createVideoRef() {
  const video = document.createElement('video')
  Object.defineProperty(video, 'duration', { get: () => 60, configurable: true })
  Object.defineProperty(video, 'currentTime', {
    get: () => 0,
    set: () => {},
    configurable: true,
  })
  Object.defineProperty(video, 'paused', { get: () => true, configurable: true })
  Object.defineProperty(video, 'volume', {
    get: () => 1,
    set: () => {},
    configurable: true,
  })
  Object.defineProperty(video, 'muted', {
    get: () => false,
    set: () => {},
    configurable: true,
  })
  return { current: video }
}

beforeEach(() => {
  vi.restoreAllMocks()
  mockLastMessage = null
  usePreviewStore.setState({
    position: 0,
    duration: 60,
    volume: 1,
    muted: false,
  })
})

describe('BottomHUD', () => {
  it('renders playback controls', () => {
    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    expect(screen.getByTestId('theater-bottom-hud')).toBeDefined()
    expect(screen.getByTestId('player-controls')).toBeDefined()
  })

  it('does not show render progress when no events received', () => {
    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    expect(screen.queryByTestId('render-progress')).toBeNull()
  })

  it('shows render progress when RENDER_PROGRESS event arrives', () => {
    mockLastMessage = {
      data: JSON.stringify({
        type: 'render_progress',
        payload: { progress: 0.45, eta_seconds: 120 },
      }),
    } as MessageEvent

    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    expect(screen.getByTestId('render-progress')).toBeDefined()
    expect(screen.getByText('45% — ETA 2m 0s')).toBeDefined()
  })

  it('shows render progress without ETA when eta_seconds is null', () => {
    mockLastMessage = {
      data: JSON.stringify({
        type: 'render_progress',
        payload: { progress: 0.75, eta_seconds: null },
      }),
    } as MessageEvent

    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    expect(screen.getByTestId('render-progress')).toBeDefined()
    expect(screen.getByText('75%')).toBeDefined()
  })

  it('has correct data-testid', () => {
    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    expect(screen.getByTestId('theater-bottom-hud')).toBeDefined()
  })
})
