import { render, screen, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { usePreviewStore } from '../../stores/previewStore'
import PreviewStatus from '../PreviewStatus'

/** Create a mock video element with controllable buffered ranges. */
function createMockVideo(ranges: Array<[number, number]> = []) {
  const video = document.createElement('video')

  const buffered = {
    get length() {
      return ranges.length
    },
    start(i: number) {
      return ranges[i][0]
    },
    end(i: number) {
      return ranges[i][1]
    },
  }

  Object.defineProperty(video, 'buffered', {
    get: () => buffered,
    configurable: true,
  })

  return { video, setRanges: (r: Array<[number, number]>) => { ranges = r } }
}

beforeEach(() => {
  usePreviewStore.setState({
    status: 'ready',
    progress: 0,
    duration: 60,
  })
})

describe('PreviewStatus', () => {
  it('displays seek latency after a seek operation', () => {
    const { video } = createMockVideo()
    const ref = { current: video }

    render(<PreviewStatus videoRef={ref} />)

    // Mock performance.now for deterministic latency AFTER render
    // so event listeners are already attached
    const nowSpy = vi.spyOn(performance, 'now')
    nowSpy.mockReturnValueOnce(100) // seeking start
    nowSpy.mockReturnValueOnce(145) // seeked end

    act(() => {
      video.dispatchEvent(new Event('seeking'))
      video.dispatchEvent(new Event('seeked'))
    })

    expect(screen.getByTestId('seek-latency').textContent).toBe('Seek: 45ms')
    nowSpy.mockRestore()
  })

  it('displays buffer amount as visual bar', () => {
    const { video, setRanges } = createMockVideo([[0, 10]])
    const ref = { current: video }

    usePreviewStore.setState({ duration: 100 })
    render(<PreviewStatus videoRef={ref} />)

    // Trigger buffer update via timeupdate
    act(() => {
      video.dispatchEvent(new Event('timeupdate'))
    })

    const bar = screen.getByTestId('buffer-bar')
    expect(bar.style.width).toBe('10%')
    expect(screen.getByTestId('buffer-seconds').textContent).toBe('10.0s')

    // Update buffer ranges
    setRanges([[0, 30]])
    act(() => {
      video.dispatchEvent(new Event('timeupdate'))
    })

    expect(bar.style.width).toBe('30%')
    expect(screen.getByTestId('buffer-seconds').textContent).toBe('30.0s')
  })

  it('shows generation progress during creating status', () => {
    const { video } = createMockVideo()
    const ref = { current: video }

    usePreviewStore.setState({ status: 'generating', progress: 0.42 })
    render(<PreviewStatus videoRef={ref} />)

    expect(screen.getByTestId('generation-progress').textContent).toBe(
      'Generating: 42%',
    )
  })

  it('does not show generation progress when status is ready', () => {
    const { video } = createMockVideo()
    const ref = { current: video }

    usePreviewStore.setState({ status: 'ready', progress: 0 })
    render(<PreviewStatus videoRef={ref} />)

    expect(screen.queryByTestId('generation-progress')).toBeNull()
  })

  it('updates buffer on progress event (universal buffer tracking)', () => {
    const { video } = createMockVideo([[0, 5]])
    const ref = { current: video }

    usePreviewStore.setState({ duration: 50 })
    render(<PreviewStatus videoRef={ref} />)

    act(() => {
      video.dispatchEvent(new Event('progress'))
    })

    expect(screen.getByTestId('buffer-bar').style.width).toBe('10%')
  })
})
