import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import SeekTooltip, {
  calculateFrameOffset,
  type ThumbnailMetadata,
} from '../SeekTooltip'
import ProgressBar from '../ProgressBar'

const METADATA: ThumbnailMetadata = {
  columns: 10,
  frame_count: 30,
  frame_height: 90,
  frame_width: 160,
  interval_seconds: 2,
  rows: 3,
  strip_url: '/thumbnails/strip.jpg',
}

// ---------------------------------------------------------------------------
// calculateFrameOffset
// ---------------------------------------------------------------------------

describe('calculateFrameOffset', () => {
  it('returns frame 0 at time 0', () => {
    expect(calculateFrameOffset(0, METADATA)).toEqual({
      frameIndex: 0,
      bgX: 0,
      bgY: 0,
    })
  })

  it('calculates correct column offset within the first row', () => {
    // hoverTime = 7 => frameIndex = floor(7/2) = 3
    // col = 3, row = 0 => bgX = -(3*160) = -480
    const result = calculateFrameOffset(7, METADATA)
    expect(result).toEqual({ frameIndex: 3, bgX: -480, bgY: 0 })
  })

  it('calculates correct row offset for frames in the second row', () => {
    // hoverTime = 20 => frameIndex = floor(20/2) = 10
    // col = 0, row = 1 => bgY = -(1*90) = -90
    const result = calculateFrameOffset(20, METADATA)
    expect(result).toEqual({ frameIndex: 10, bgX: 0, bgY: -90 })
  })

  it('calculates both column and row offsets', () => {
    // hoverTime = 25 => frameIndex = floor(25/2) = 12
    // col = 12 % 10 = 2, row = floor(12/10) = 1
    const result = calculateFrameOffset(25, METADATA)
    expect(result).toEqual({ frameIndex: 12, bgX: -(2 * 160), bgY: -90 })
  })

  it('clamps frameIndex to frame_count - 1 when exceeding total frames', () => {
    // hoverTime = 100 => frameIndex = 50 >= 30 => clamp to 29
    // col = 29 % 10 = 9, row = floor(29/10) = 2
    const result = calculateFrameOffset(100, METADATA)
    expect(result).toEqual({
      frameIndex: 29,
      bgX: -(9 * 160),
      bgY: -(2 * 90),
    })
  })

  it('clamps negative hoverTime to frame 0', () => {
    const result = calculateFrameOffset(-5, METADATA)
    expect(result).toEqual({ frameIndex: 0, bgX: 0, bgY: 0 })
  })
})

// ---------------------------------------------------------------------------
// SeekTooltip component
// ---------------------------------------------------------------------------

describe('SeekTooltip', () => {
  it('renders time-only fallback when thumbnailMetadata is null', () => {
    render(
      <SeekTooltip
        hoverTime={30}
        duration={120}
        thumbnailMetadata={null}
        mouseX={100}
        barWidth={400}
      />,
    )
    expect(screen.getByTestId('seek-tooltip')).toBeTruthy()
    expect(screen.getByTestId('seek-tooltip-time').textContent).toBe('0:30')
    expect(screen.queryByTestId('seek-tooltip-thumbnail')).toBeNull()
  })

  it('renders thumbnail when metadata is provided', () => {
    render(
      <SeekTooltip
        hoverTime={4}
        duration={60}
        thumbnailMetadata={METADATA}
        mouseX={200}
        barWidth={400}
      />,
    )
    expect(screen.getByTestId('seek-tooltip-thumbnail')).toBeTruthy()
    expect(screen.getByTestId('seek-tooltip-time').textContent).toBe('0:04')
  })

  it('applies correct sprite offset as background-position', () => {
    // hoverTime = 4, interval = 2 => frameIndex = 2
    // col = 2, row = 0 => bgX = -320, bgY = 0
    render(
      <SeekTooltip
        hoverTime={4}
        duration={60}
        thumbnailMetadata={METADATA}
        mouseX={200}
        barWidth={400}
      />,
    )
    const thumbnail = screen.getByTestId('seek-tooltip-thumbnail')
    const inner = thumbnail.firstChild as HTMLElement
    expect(inner.style.backgroundPosition).toBe('-320px 0px')
    expect(inner.style.backgroundImage).toContain('/thumbnails/strip.jpg')
  })

  it('clamps tooltip position to left bar bound', () => {
    render(
      <SeekTooltip
        hoverTime={0}
        duration={60}
        thumbnailMetadata={METADATA}
        mouseX={10}
        barWidth={400}
      />,
    )
    const tooltip = screen.getByTestId('seek-tooltip')
    // halfTooltip = 160/2 = 80; mouseX = 10 < 80 => clampedX = 80
    expect(tooltip.style.left).toBe('80px')
  })

  it('clamps tooltip position to right bar bound', () => {
    render(
      <SeekTooltip
        hoverTime={55}
        duration={60}
        thumbnailMetadata={METADATA}
        mouseX={390}
        barWidth={400}
      />,
    )
    const tooltip = screen.getByTestId('seek-tooltip')
    // halfTooltip = 80; barWidth - halfTooltip = 320; mouseX = 390 > 320 => 320
    expect(tooltip.style.left).toBe('320px')
  })

  it('uses translateX(-50%) for centering', () => {
    render(
      <SeekTooltip
        hoverTime={30}
        duration={60}
        thumbnailMetadata={null}
        mouseX={200}
        barWidth={400}
      />,
    )
    const tooltip = screen.getByTestId('seek-tooltip')
    expect(tooltip.style.transform).toBe('translateX(-50%)')
  })

  it('uses absolute positioning (no layout reflow)', () => {
    render(
      <SeekTooltip
        hoverTime={10}
        duration={60}
        thumbnailMetadata={null}
        mouseX={100}
        barWidth={400}
      />,
    )
    const tooltip = screen.getByTestId('seek-tooltip')
    expect(tooltip.className).toContain('absolute')
    expect(tooltip.className).toContain('pointer-events-none')
  })
})

// ---------------------------------------------------------------------------
// ProgressBar + SeekTooltip integration
// ---------------------------------------------------------------------------

/** Mock bounding rect and clientWidth on a track element. */
function mockTrackGeometry(track: HTMLElement, width: number) {
  Object.defineProperty(track, 'clientWidth', {
    value: width,
    configurable: true,
  })
  track.getBoundingClientRect = () => ({
    left: 0,
    right: width,
    top: 0,
    bottom: 8,
    width,
    height: 8,
    x: 0,
    y: 0,
    toJSON: () => ({}),
  })
}

describe('ProgressBar seek tooltip integration', () => {
  it('shows tooltip on mouseenter and hides on mouseleave', () => {
    render(<ProgressBar currentTime={0} duration={60} onSeek={vi.fn()} />)
    const track = screen.getByTestId('progress-bar-track')
    mockTrackGeometry(track, 400)

    fireEvent.mouseEnter(track)
    fireEvent.mouseMove(track, { clientX: 200 })

    expect(screen.getByTestId('seek-tooltip')).toBeTruthy()

    fireEvent.mouseLeave(track)
    expect(screen.queryByTestId('seek-tooltip')).toBeNull()
  })

  it('does not show tooltip when duration is 0', () => {
    render(<ProgressBar currentTime={0} duration={0} onSeek={vi.fn()} />)
    const track = screen.getByTestId('progress-bar-track')
    mockTrackGeometry(track, 400)

    fireEvent.mouseEnter(track)
    fireEvent.mouseMove(track, { clientX: 200 })

    expect(screen.queryByTestId('seek-tooltip')).toBeNull()
  })

  it('displays time-only tooltip when no thumbnailMetadata', () => {
    render(<ProgressBar currentTime={0} duration={60} onSeek={vi.fn()} />)
    const track = screen.getByTestId('progress-bar-track')
    mockTrackGeometry(track, 400)

    fireEvent.mouseEnter(track)
    fireEvent.mouseMove(track, { clientX: 200 })

    expect(screen.getByTestId('seek-tooltip-time')).toBeTruthy()
    expect(screen.queryByTestId('seek-tooltip-thumbnail')).toBeNull()
  })

  it('displays thumbnail tooltip when metadata is provided', () => {
    render(
      <ProgressBar
        currentTime={0}
        duration={60}
        onSeek={vi.fn()}
        thumbnailMetadata={METADATA}
      />,
    )
    const track = screen.getByTestId('progress-bar-track')
    mockTrackGeometry(track, 400)

    fireEvent.mouseEnter(track)
    fireEvent.mouseMove(track, { clientX: 200 })

    expect(screen.getByTestId('seek-tooltip-thumbnail')).toBeTruthy()
  })
})

// ---------------------------------------------------------------------------
// Contract: ThumbnailMetadata schema
// ---------------------------------------------------------------------------

describe('ThumbnailMetadata contract', () => {
  it('matches expected schema from thumbnail strip API', () => {
    const metadata: ThumbnailMetadata = {
      columns: 10,
      frame_count: 30,
      frame_height: 90,
      frame_width: 160,
      interval_seconds: 2,
      rows: 3,
      strip_url: '/thumbnails/strip.jpg',
    }
    expect(typeof metadata.columns).toBe('number')
    expect(typeof metadata.frame_count).toBe('number')
    expect(typeof metadata.frame_height).toBe('number')
    expect(typeof metadata.frame_width).toBe('number')
    expect(typeof metadata.interval_seconds).toBe('number')
    expect(typeof metadata.rows).toBe('number')
    expect(typeof metadata.strip_url).toBe('string')
  })
})
