import { act, render, screen } from '@testing-library/react'
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
    frame_count: null,
    fps: null,
    encoder_name: null,
    encoder_type: null,
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

  it('shows render progress with percentage and ETA for running job', () => {
    useRenderStore.setState({
      jobs: [makeJob({ progress: 0.45, eta_seconds: 120 })],
    })

    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    expect(screen.getByTestId('render-progress')).toBeDefined()
    const stats = screen.getByTestId('render-stats')
    expect(stats.textContent).toContain('45%')
    expect(stats.textContent).toContain('ETA 2m 0s')
  })

  it('formats ETA correctly for various durations', () => {
    useRenderStore.setState({
      jobs: [makeJob({ progress: 0.5, eta_seconds: 150 })],
    })

    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    expect(screen.getByTestId('render-stats').textContent).toContain('ETA 2m 30s')
  })

  it('shows "Calculating..." when eta_seconds is null', () => {
    useRenderStore.setState({
      jobs: [makeJob({ progress: 0.75, eta_seconds: null })],
    })

    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    expect(screen.getByTestId('render-progress')).toBeDefined()
    const stats = screen.getByTestId('render-stats')
    expect(stats.textContent).toContain('75%')
    expect(stats.textContent).toContain('Calculating...')
  })

  it('shows speed ratio when available', () => {
    useRenderStore.setState({
      jobs: [makeJob({ progress: 0.5, eta_seconds: 60, speed_ratio: 1.5 })],
    })

    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    expect(screen.getByTestId('render-speed')).toBeDefined()
    expect(screen.getByTestId('render-speed').textContent).toContain('1.5x')
  })

  it('omits speed ratio when speed_ratio is null', () => {
    useRenderStore.setState({
      jobs: [makeJob({ progress: 0.5, eta_seconds: 60, speed_ratio: null })],
    })

    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    expect(screen.queryByTestId('render-speed')).toBeNull()
  })

  it('does not show render progress for completed jobs', () => {
    useRenderStore.setState({
      jobs: [makeJob({ status: 'completed', progress: 1.0 })],
    })

    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    expect(screen.queryByTestId('render-progress')).toBeNull()
  })

  it('hides indicators when job transitions from running to completed', () => {
    useRenderStore.setState({
      jobs: [makeJob({ status: 'running', progress: 0.9, eta_seconds: 10 })],
    })

    const videoRef = createVideoRef()
    const { rerender } = render(<BottomHUD videoRef={videoRef} />)
    expect(screen.getByTestId('render-progress')).toBeDefined()

    act(() => {
      useRenderStore.setState({
        jobs: [makeJob({ status: 'completed', progress: 1.0 })],
      })
    })
    rerender(<BottomHUD videoRef={videoRef} />)
    expect(screen.queryByTestId('render-progress')).toBeNull()
  })

  it('shows progress for the first running job when multiple jobs exist', () => {
    useRenderStore.setState({
      jobs: [
        makeJob({ id: 'job-completed', status: 'completed', progress: 1.0 }),
        makeJob({ id: 'job-active', status: 'running', progress: 0.33, eta_seconds: 200 }),
        makeJob({ id: 'job-queued', status: 'queued', progress: 0 }),
      ],
    })

    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    const stats = screen.getByTestId('render-stats')
    expect(stats.textContent).toContain('33%')
    expect(stats.textContent).toContain('ETA 3m 20s')
  })

  it('has correct data-testid', () => {
    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    expect(screen.getByTestId('theater-bottom-hud')).toBeDefined()
  })

  it('shows encoder name and type when both are non-null', async () => {
    useRenderStore.setState({
      jobs: [makeJob({ progress: 0.5, encoder_name: 'h264_nvenc', encoder_type: 'HW' })],
    })

    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    const encoder = screen.getByTestId('render-encoder')
    expect(encoder.textContent).toContain('h264_nvenc')
    const encoderType = screen.getByTestId('render-encoder-type')
    expect(encoderType.textContent).toContain('HW')
  })

  it('shows encoder name without type when encoder_type is null', async () => {
    useRenderStore.setState({
      jobs: [makeJob({ progress: 0.5, encoder_name: 'libx264', encoder_type: null })],
    })

    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    const encoder = screen.getByTestId('render-encoder')
    expect(encoder.textContent).toContain('libx264')
    expect(screen.queryByTestId('render-encoder-type')).toBeNull()
  })

  it('hides encoder section when encoder_name is null', () => {
    useRenderStore.setState({
      jobs: [makeJob({ progress: 0.5, encoder_name: null })],
    })

    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    expect(screen.queryByTestId('render-encoder')).toBeNull()
  })

  it('shows frame count when non-null', () => {
    useRenderStore.setState({
      jobs: [makeJob({ progress: 0.5, frame_count: 1200 })],
    })

    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    const frameCount = screen.getByTestId('render-frame-count')
    expect(frameCount.textContent).toContain('1200f')
  })

  it('hides frame count when null', () => {
    useRenderStore.setState({
      jobs: [makeJob({ progress: 0.5, frame_count: null })],
    })

    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    expect(screen.queryByTestId('render-frame-count')).toBeNull()
  })

  it('shows fps when non-null', () => {
    useRenderStore.setState({
      jobs: [makeJob({ progress: 0.5, fps: 29.97 })],
    })

    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    const fpsEl = screen.getByTestId('render-fps')
    expect(fpsEl.textContent).toContain('30.0 fps')
  })

  it('hides fps when null', () => {
    useRenderStore.setState({
      jobs: [makeJob({ progress: 0.5, fps: null })],
    })

    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    expect(screen.queryByTestId('render-fps')).toBeNull()
  })

  it('shows all enriched fields together for SW encoder', () => {
    useRenderStore.setState({
      jobs: [
        makeJob({
          progress: 0.6,
          eta_seconds: 30,
          encoder_name: 'libx264',
          encoder_type: 'SW',
          frame_count: 600,
          fps: 24.0,
        }),
      ],
    })

    const videoRef = createVideoRef()
    render(<BottomHUD videoRef={videoRef} />)
    expect(screen.getByTestId('render-encoder').textContent).toContain('libx264')
    expect(screen.getByTestId('render-encoder-type').textContent).toContain('SW')
    expect(screen.getByTestId('render-frame-count').textContent).toContain('600f')
    expect(screen.getByTestId('render-fps').textContent).toContain('24.0 fps')
  })
})
