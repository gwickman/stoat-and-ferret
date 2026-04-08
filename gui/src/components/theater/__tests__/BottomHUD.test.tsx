import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import BottomHUD from '../BottomHUD'
import { usePreviewStore } from '../../../stores/previewStore'
import { useRenderStore } from '../../../stores/renderStore'
import type { RenderJob } from '../../../stores/renderStore'

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

function makeJob(overrides: Partial<RenderJob> = {}): RenderJob {
  return {
    id: 'job-1',
    project_id: 'proj-1',
    status: 'running',
    output_path: '/out/video.mp4',
    output_format: 'mp4',
    quality_preset: 'high',
    progress: 0,
    eta_seconds: null,
    speed_ratio: null,
    error_message: null,
    retry_count: 0,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    completed_at: null,
    ...overrides,
  }
}

beforeEach(() => {
  vi.restoreAllMocks()
  useRenderStore.setState({ jobs: [] })
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

  it('does not show render progress when no active jobs', () => {
    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    expect(screen.queryByTestId('render-progress')).toBeNull()
  })

  it('shows render progress from renderStore for running job', () => {
    useRenderStore.setState({
      jobs: [makeJob({ progress: 0.45, eta_seconds: 120 })],
    })

    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    expect(screen.getByTestId('render-progress')).toBeDefined()
    expect(screen.getByText('45% — ETA 2m 0s')).toBeDefined()
  })

  it('shows render progress without ETA when eta_seconds is null', () => {
    useRenderStore.setState({
      jobs: [makeJob({ progress: 0.75, eta_seconds: null })],
    })

    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    expect(screen.getByTestId('render-progress')).toBeDefined()
    expect(screen.getByText('75%')).toBeDefined()
  })

  it('does not show render progress for completed jobs', () => {
    useRenderStore.setState({
      jobs: [makeJob({ status: 'completed', progress: 1.0 })],
    })

    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    expect(screen.queryByTestId('render-progress')).toBeNull()
  })

  it('has correct data-testid', () => {
    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    expect(screen.getByTestId('theater-bottom-hud')).toBeDefined()
  })
})
