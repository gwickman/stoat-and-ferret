import { render, screen, fireEvent, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import TheaterMode from '../TheaterMode'
import { useTheaterStore } from '../../../stores/theaterStore'

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

beforeEach(() => {
  vi.restoreAllMocks()
  vi.useFakeTimers()
  useTheaterStore.getState().reset()
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
})
