import { render, screen, fireEvent, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { usePreviewStore } from '../../stores/previewStore'
import ProgressBar, { formatTime } from '../ProgressBar'
import VolumeSlider from '../VolumeSlider'
import PlayerControls from '../PlayerControls'

/** Create a mock video element with controllable properties. */
function createMockVideo(overrides: Partial<HTMLVideoElement> = {}) {
  const video = document.createElement('video')
  let _currentTime = 0
  let _volume = 1
  let _muted = false
  const _duration = overrides.duration ?? 60

  Object.defineProperty(video, 'duration', {
    get: () => _duration,
    configurable: true,
  })
  Object.defineProperty(video, 'currentTime', {
    get: () => _currentTime,
    set: (v: number) => { _currentTime = v },
    configurable: true,
  })
  Object.defineProperty(video, 'volume', {
    get: () => _volume,
    set: (v: number) => { _volume = v },
    configurable: true,
  })
  Object.defineProperty(video, 'muted', {
    get: () => _muted,
    set: (v: boolean) => { _muted = v },
    configurable: true,
  })
  Object.defineProperty(video, 'paused', {
    get: () => true,
    configurable: true,
  })

  video.play = vi.fn(() => {
    Object.defineProperty(video, 'paused', { get: () => false, configurable: true })
    video.dispatchEvent(new Event('play'))
    return Promise.resolve()
  })
  video.pause = vi.fn(() => {
    Object.defineProperty(video, 'paused', { get: () => true, configurable: true })
    video.dispatchEvent(new Event('pause'))
  })

  return video
}

beforeEach(() => {
  usePreviewStore.setState({
    position: 0,
    duration: 0,
    volume: 1,
    muted: false,
  })
})

describe('formatTime', () => {
  it('formats seconds as mm:ss', () => {
    expect(formatTime(0)).toBe('0:00')
    expect(formatTime(5)).toBe('0:05')
    expect(formatTime(65)).toBe('1:05')
    expect(formatTime(599)).toBe('9:59')
  })

  it('formats as hh:mm:ss for durations >= 1 hour', () => {
    expect(formatTime(3600)).toBe('1:00:00')
    expect(formatTime(3661)).toBe('1:01:01')
    expect(formatTime(7200)).toBe('2:00:00')
  })

  it('handles negative values as 0:00', () => {
    expect(formatTime(-5)).toBe('0:00')
  })

  it('floors fractional seconds', () => {
    expect(formatTime(5.9)).toBe('0:05')
    expect(formatTime(59.99)).toBe('0:59')
  })
})

describe('ProgressBar', () => {
  it('displays current time and duration', () => {
    render(<ProgressBar currentTime={30} duration={120} onSeek={vi.fn()} />)

    expect(screen.getByTestId('time-current').textContent).toBe('0:30')
    expect(screen.getByTestId('time-duration').textContent).toBe('2:00')
  })

  it('shows correct fill percentage', () => {
    render(<ProgressBar currentTime={30} duration={60} onSeek={vi.fn()} />)

    const fill = screen.getByTestId('progress-bar-fill')
    expect(fill.style.width).toBe('50%')
  })

  it('handles zero duration without error', () => {
    render(<ProgressBar currentTime={0} duration={0} onSeek={vi.fn()} />)

    const fill = screen.getByTestId('progress-bar-fill')
    expect(fill.style.width).toBe('0%')
  })

  it('click-to-seek calculates correct position', () => {
    const onSeek = vi.fn()
    render(<ProgressBar currentTime={0} duration={100} onSeek={onSeek} />)

    const track = screen.getByTestId('progress-bar-track')

    // Mock getBoundingClientRect for the track element
    vi.spyOn(track, 'getBoundingClientRect').mockReturnValue({
      left: 0,
      width: 200,
      top: 0,
      right: 200,
      bottom: 10,
      height: 10,
      x: 0,
      y: 0,
      toJSON: () => {},
    })

    fireEvent.click(track, { clientX: 100 })

    // Click at 100/200 = 0.5, so seek to 50s of 100s
    expect(onSeek).toHaveBeenCalledWith(50)
  })

  it('clamps seek to valid range', () => {
    const onSeek = vi.fn()
    render(<ProgressBar currentTime={0} duration={100} onSeek={onSeek} />)

    const track = screen.getByTestId('progress-bar-track')
    vi.spyOn(track, 'getBoundingClientRect').mockReturnValue({
      left: 100,
      width: 200,
      top: 0,
      right: 300,
      bottom: 10,
      height: 10,
      x: 100,
      y: 0,
      toJSON: () => {},
    })

    // Click before the bar (clientX < left)
    fireEvent.click(track, { clientX: 50 })
    expect(onSeek).toHaveBeenCalledWith(0)
  })

  it('has correct ARIA attributes', () => {
    render(<ProgressBar currentTime={30} duration={120} onSeek={vi.fn()} />)

    const bar = screen.getByTestId('progress-bar-track')
    expect(bar.getAttribute('role')).toBe('progressbar')
    expect(bar.getAttribute('aria-valuenow')).toBe('30')
    expect(bar.getAttribute('aria-valuemin')).toBe('0')
    expect(bar.getAttribute('aria-valuemax')).toBe('120')
    expect(bar.getAttribute('aria-label')).toBe('Playback progress')
  })
})

describe('VolumeSlider', () => {
  it('renders volume slider with correct value', () => {
    render(
      <VolumeSlider
        volume={0.5}
        muted={false}
        onVolumeChange={vi.fn()}
        onMuteToggle={vi.fn()}
      />,
    )

    const slider = screen.getByTestId('volume-slider') as HTMLInputElement
    expect(slider.value).toBe('0.5')
  })

  it('updates volume on slider change', () => {
    const onVolumeChange = vi.fn()
    render(
      <VolumeSlider
        volume={0.5}
        muted={false}
        onVolumeChange={onVolumeChange}
        onMuteToggle={vi.fn()}
      />,
    )

    const slider = screen.getByTestId('volume-slider')
    fireEvent.change(slider, { target: { value: '0.75' } })

    expect(onVolumeChange).toHaveBeenCalledWith(0.75)
  })

  it('shows muted icon when muted', () => {
    render(
      <VolumeSlider
        volume={0.5}
        muted={true}
        onVolumeChange={vi.fn()}
        onMuteToggle={vi.fn()}
      />,
    )

    const btn = screen.getByTestId('mute-btn')
    expect(btn.getAttribute('aria-label')).toBe('Unmute')
  })

  it('shows unmuted icon when not muted', () => {
    render(
      <VolumeSlider
        volume={0.5}
        muted={false}
        onVolumeChange={vi.fn()}
        onMuteToggle={vi.fn()}
      />,
    )

    const btn = screen.getByTestId('mute-btn')
    expect(btn.getAttribute('aria-label')).toBe('Mute')
  })

  it('calls onMuteToggle on mute button click', () => {
    const onMuteToggle = vi.fn()
    render(
      <VolumeSlider
        volume={0.5}
        muted={false}
        onVolumeChange={vi.fn()}
        onMuteToggle={onMuteToggle}
      />,
    )

    fireEvent.click(screen.getByTestId('mute-btn'))
    expect(onMuteToggle).toHaveBeenCalledOnce()
  })

  it('displays volume as 0 when muted', () => {
    render(
      <VolumeSlider
        volume={0.8}
        muted={true}
        onVolumeChange={vi.fn()}
        onMuteToggle={vi.fn()}
      />,
    )

    const slider = screen.getByTestId('volume-slider') as HTMLInputElement
    expect(slider.value).toBe('0')
  })

  it('has correct ARIA label on slider', () => {
    render(
      <VolumeSlider
        volume={0.5}
        muted={false}
        onVolumeChange={vi.fn()}
        onMuteToggle={vi.fn()}
      />,
    )

    const slider = screen.getByTestId('volume-slider')
    expect(slider.getAttribute('aria-label')).toBe('Volume')
  })
})

describe('PlayerControls', () => {
  let video: HTMLVideoElement

  beforeEach(() => {
    video = createMockVideo({ duration: 60 } as Partial<HTMLVideoElement>)
  })

  function renderControls() {
    const ref = { current: video }
    return render(<PlayerControls videoRef={ref} />)
  }

  describe('play/pause toggle', () => {
    it('shows play icon when paused', () => {
      renderControls()

      const btn = screen.getByTestId('play-pause-btn')
      expect(btn.getAttribute('aria-label')).toBe('Play')
    })

    it('toggles to pause on click', async () => {
      renderControls()

      const btn = screen.getByTestId('play-pause-btn')
      await act(async () => {
        fireEvent.click(btn)
      })

      expect(video.play).toHaveBeenCalled()
      expect(btn.getAttribute('aria-label')).toBe('Pause')
    })

    it('toggles back to play on second click', async () => {
      renderControls()

      const btn = screen.getByTestId('play-pause-btn')
      await act(async () => {
        fireEvent.click(btn)
      })
      expect(btn.getAttribute('aria-label')).toBe('Pause')

      await act(async () => {
        fireEvent.click(btn)
      })
      expect(video.pause).toHaveBeenCalled()
      expect(btn.getAttribute('aria-label')).toBe('Play')
    })
  })

  describe('skip buttons', () => {
    it('skip forward offsets by +5 seconds', () => {
      video.currentTime = 10
      renderControls()

      fireEvent.click(screen.getByTestId('skip-fwd-btn'))

      expect(video.currentTime).toBe(15)
    })

    it('skip backward offsets by -5 seconds', () => {
      video.currentTime = 10
      renderControls()

      fireEvent.click(screen.getByTestId('skip-back-btn'))

      expect(video.currentTime).toBe(5)
    })

    it('clamps skip backward to 0', () => {
      video.currentTime = 2
      renderControls()

      fireEvent.click(screen.getByTestId('skip-back-btn'))

      expect(video.currentTime).toBe(0)
    })

    it('clamps skip forward to duration', () => {
      video.currentTime = 58
      renderControls()

      fireEvent.click(screen.getByTestId('skip-fwd-btn'))

      expect(video.currentTime).toBe(60)
    })
  })

  describe('keyboard accessibility', () => {
    it('Space toggles play/pause', async () => {
      renderControls()

      const container = screen.getByTestId('player-controls')
      await act(async () => {
        fireEvent.keyDown(container, { key: ' ' })
      })

      expect(video.play).toHaveBeenCalled()
    })

    it('ArrowRight seeks forward 5 seconds', () => {
      video.currentTime = 10
      renderControls()

      const container = screen.getByTestId('player-controls')
      fireEvent.keyDown(container, { key: 'ArrowRight' })

      expect(video.currentTime).toBe(15)
    })

    it('ArrowLeft seeks backward 5 seconds', () => {
      video.currentTime = 10
      renderControls()

      const container = screen.getByTestId('player-controls')
      fireEvent.keyDown(container, { key: 'ArrowLeft' })

      expect(video.currentTime).toBe(5)
    })

    it('ArrowUp increases volume by 0.1', () => {
      usePreviewStore.setState({ volume: 0.5 })
      renderControls()

      const container = screen.getByTestId('player-controls')
      fireEvent.keyDown(container, { key: 'ArrowUp' })

      expect(video.volume).toBeCloseTo(0.6, 1)
    })

    it('ArrowDown decreases volume by 0.1', () => {
      usePreviewStore.setState({ volume: 0.5 })
      renderControls()

      const container = screen.getByTestId('player-controls')
      fireEvent.keyDown(container, { key: 'ArrowDown' })

      expect(video.volume).toBeCloseTo(0.4, 1)
    })

    it('ArrowDown clamps volume to 0', () => {
      usePreviewStore.setState({ volume: 0.05 })
      renderControls()

      const container = screen.getByTestId('player-controls')
      fireEvent.keyDown(container, { key: 'ArrowDown' })

      expect(video.volume).toBe(0)
    })

    it('ArrowUp clamps volume to 1', () => {
      usePreviewStore.setState({ volume: 0.95 })
      renderControls()

      const container = screen.getByTestId('player-controls')
      fireEvent.keyDown(container, { key: 'ArrowUp' })

      expect(video.volume).toBe(1)
    })
  })

  describe('mute toggle', () => {
    it('mute sets video.muted to true', () => {
      renderControls()

      fireEvent.click(screen.getByTestId('mute-btn'))

      expect(video.muted).toBe(true)
    })

    it('unmute restores previous volume', () => {
      usePreviewStore.setState({ volume: 0.7 })
      renderControls()

      // Mute
      fireEvent.click(screen.getByTestId('mute-btn'))
      expect(video.muted).toBe(true)

      // Unmute
      fireEvent.click(screen.getByTestId('mute-btn'))
      expect(video.muted).toBe(false)
      expect(video.volume).toBeCloseTo(0.7, 1)
    })
  })

  describe('ARIA and accessibility', () => {
    it('has toolbar role with label', () => {
      renderControls()

      const container = screen.getByTestId('player-controls')
      expect(container.getAttribute('role')).toBe('toolbar')
      expect(container.getAttribute('aria-label')).toBe('Video player controls')
    })

    it('is focusable via tabIndex', () => {
      renderControls()

      const container = screen.getByTestId('player-controls')
      expect(container.getAttribute('tabindex')).toBe('0')
    })

    it('all buttons have aria-labels', () => {
      renderControls()

      expect(screen.getByTestId('play-pause-btn').getAttribute('aria-label')).toBeTruthy()
      expect(screen.getByTestId('skip-back-btn').getAttribute('aria-label')).toBeTruthy()
      expect(screen.getByTestId('skip-fwd-btn').getAttribute('aria-label')).toBeTruthy()
      expect(screen.getByTestId('mute-btn').getAttribute('aria-label')).toBeTruthy()
    })
  })

  describe('video event sync', () => {
    it('updates store position on timeupdate', () => {
      renderControls()

      video.currentTime = 25
      act(() => {
        video.dispatchEvent(new Event('timeupdate'))
      })

      expect(usePreviewStore.getState().position).toBe(25)
    })

    it('updates store duration on durationchange', () => {
      renderControls()

      act(() => {
        video.dispatchEvent(new Event('durationchange'))
      })

      expect(usePreviewStore.getState().duration).toBe(60)
    })
  })
})
