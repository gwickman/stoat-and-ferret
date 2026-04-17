import { render, screen, fireEvent, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import TheaterMode from '../TheaterMode'
import { useTheaterStore } from '../../../stores/theaterStore'
import { useRenderStore } from '../../../stores/renderStore'
import type { RenderJob } from '../../../stores/renderStore'

vi.mock('../../../hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    state: 'disconnected' as const,
    send: vi.fn(),
    lastMessage: null,
  }),
}))

vi.mock('../../../hooks/useProjects', () => ({
  useProjects: () => ({
    projects: [],
    total: 0,
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
}))

function makeRunningJob(overrides: Partial<RenderJob> = {}): RenderJob {
  return {
    id: 'job-1',
    project_id: 'proj-1',
    status: 'running',
    output_path: '/out/video.mp4',
    output_format: 'mp4',
    quality_preset: 'standard',
    progress: 0.5,
    eta_seconds: null,
    speed_ratio: null,
    frame_count: null,
    fps: null,
    encoder_name: null,
    encoder_type: null,
    error_message: null,
    retry_count: 0,
    created_at: '',
    updated_at: '',
    completed_at: null,
    ...overrides,
  }
}

beforeEach(() => {
  vi.restoreAllMocks()
  vi.useFakeTimers()
  useTheaterStore.getState().reset()
  useRenderStore.getState().reset()
})

afterEach(() => {
  vi.useRealTimers()
})

function renderTheater() {
  return render(
    <TheaterMode>
      <div data-testid="child-content">Video Here</div>
    </TheaterMode>,
  )
}

describe('TheaterMode', () => {
  it('passes through children when not in fullscreen', () => {
    renderTheater()
    expect(screen.getByTestId('child-content')).toBeDefined()
    expect(screen.queryByTestId('theater-container')).toBeNull()
  })

  it('renders container and HUD when in fullscreen', () => {
    useTheaterStore.setState({ isFullscreen: true })
    renderTheater()
    expect(screen.getByTestId('theater-container')).toBeDefined()
    expect(screen.getByTestId('theater-hud-wrapper')).toBeDefined()
    expect(screen.getByTestId('child-content')).toBeDefined()
  })

  it('auto-hides HUD after 3 seconds of inactivity', () => {
    useTheaterStore.setState({ isFullscreen: true, isHUDVisible: true })
    renderTheater()

    act(() => {
      vi.advanceTimersByTime(3000)
    })

    expect(useTheaterStore.getState().isHUDVisible).toBe(false)
  })

  it('re-shows HUD on mouse movement', () => {
    useTheaterStore.setState({ isFullscreen: true, isHUDVisible: false })
    renderTheater()

    const container = screen.getByTestId('theater-container')
    fireEvent.mouseMove(container)

    expect(useTheaterStore.getState().isHUDVisible).toBe(true)
  })

  it('resets auto-hide timer on mouse movement', () => {
    useTheaterStore.setState({ isFullscreen: true, isHUDVisible: true })
    renderTheater()

    // Advance 2 seconds
    act(() => {
      vi.advanceTimersByTime(2000)
    })
    expect(useTheaterStore.getState().isHUDVisible).toBe(true)

    // Mouse move resets the timer
    const container = screen.getByTestId('theater-container')
    fireEvent.mouseMove(container)

    // Advance another 2 seconds — still visible because timer was reset
    act(() => {
      vi.advanceTimersByTime(2000)
    })
    expect(useTheaterStore.getState().isHUDVisible).toBe(true)

    // Advance the remaining 1 second — now hidden
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(useTheaterStore.getState().isHUDVisible).toBe(false)
  })

  it('cleans up timer on unmount (NFR-001)', () => {
    useTheaterStore.setState({ isFullscreen: true })
    const { unmount } = renderTheater()

    const clearTimeoutSpy = vi.spyOn(globalThis, 'clearTimeout')
    unmount()

    expect(clearTimeoutSpy).toHaveBeenCalled()
  })

  it('has correct data-testid attributes (FR-006)', () => {
    useTheaterStore.setState({ isFullscreen: true })
    renderTheater()

    expect(screen.getByTestId('theater-container')).toBeDefined()
    expect(screen.getByTestId('theater-hud-wrapper')).toBeDefined()
  })

  it('applies opacity-0 class when HUD is hidden', () => {
    useTheaterStore.setState({ isFullscreen: true, isHUDVisible: false })
    renderTheater()

    const hud = screen.getByTestId('theater-hud-wrapper')
    expect(hud.className).toContain('opacity-0')
  })

  it('applies opacity-100 class when HUD is visible', () => {
    useTheaterStore.setState({ isFullscreen: true, isHUDVisible: true })
    renderTheater()

    const hud = screen.getByTestId('theater-hud-wrapper')
    expect(hud.className).toContain('opacity-100')
  })

  // -- Frame streaming overlay (FR-003, FR-004) --

  it('shows frame overlay when active running job has frame_url (FR-003)', () => {
    useTheaterStore.setState({ isFullscreen: true })
    useRenderStore.setState({
      jobs: [makeRunningJob({ frame_url: '/api/v1/render/job-1/frame_preview.jpg' })],
    })
    renderTheater()

    const overlay = screen.getByTestId('theater-frame-overlay')
    expect(overlay).toBeDefined()
    expect((overlay as HTMLImageElement).src).toContain('frame_preview.jpg')
  })

  it('hides frame overlay when no running job exists (FR-004)', () => {
    useTheaterStore.setState({ isFullscreen: true })
    useRenderStore.setState({
      jobs: [makeRunningJob({ status: 'completed', frame_url: '/api/v1/render/job-1/frame_preview.jpg' })],
    })
    renderTheater()

    expect(screen.queryByTestId('theater-frame-overlay')).toBeNull()
  })

  it('hides frame overlay when running job has no frame_url', () => {
    useTheaterStore.setState({ isFullscreen: true })
    useRenderStore.setState({
      jobs: [makeRunningJob({ frame_url: null })],
    })
    renderTheater()

    expect(screen.queryByTestId('theater-frame-overlay')).toBeNull()
  })

  it('hides frame overlay when not in fullscreen (FR-004)', () => {
    useRenderStore.setState({
      jobs: [makeRunningJob({ frame_url: '/api/v1/render/job-1/frame_preview.jpg' })],
    })
    // isFullscreen is false by default
    renderTheater()

    // In non-fullscreen mode, children pass through directly — no theater container
    expect(screen.queryByTestId('theater-frame-overlay')).toBeNull()
  })
})
