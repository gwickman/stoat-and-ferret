import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import TimelineClip from '../TimelineClip'
import type { TimelineClip as ClipType } from '../../types/timeline'

const makeClip = (overrides: Partial<ClipType> = {}): ClipType => ({
  id: 'clip-1',
  project_id: 'proj-1',
  source_video_id: 'vid-1',
  track_id: 'track-1',
  timeline_start: 1,
  timeline_end: 4,
  in_point: 0,
  out_point: 3,
  ...overrides,
})

describe('TimelineClip', () => {
  it('renders at correct position from timeToPixel', () => {
    const clip = makeClip({ timeline_start: 2, timeline_end: 5 })
    render(
      <TimelineClip clip={clip} zoom={1} scrollOffset={0} isSelected={false} onSelect={vi.fn()} />,
    )

    const el = screen.getByTestId('clip-clip-1')
    // left = timeToPixel(2, 1, 0) = 2 * 100 * 1 - 0 = 200
    expect(el.style.left).toBe('200px')
    // width = timeToPixel(5) - timeToPixel(2) = 500 - 200 = 300
    expect(el.style.width).toBe('300px')
  })

  it('applies zoom to position and width', () => {
    const clip = makeClip({ timeline_start: 1, timeline_end: 3 })
    render(
      <TimelineClip clip={clip} zoom={2} scrollOffset={0} isSelected={false} onSelect={vi.fn()} />,
    )

    const el = screen.getByTestId('clip-clip-1')
    // left = 1 * 100 * 2 = 200
    expect(el.style.left).toBe('200px')
    // width = (3 * 100 * 2) - (1 * 100 * 2) = 600 - 200 = 400
    expect(el.style.width).toBe('400px')
  })

  it('accounts for scrollOffset', () => {
    const clip = makeClip({ timeline_start: 2, timeline_end: 4 })
    render(
      <TimelineClip clip={clip} zoom={1} scrollOffset={50} isSelected={false} onSelect={vi.fn()} />,
    )

    const el = screen.getByTestId('clip-clip-1')
    // left = 2 * 100 - 50 = 150
    expect(el.style.left).toBe('150px')
    // width = (4*100-50) - (2*100-50) = 350 - 150 = 200
    expect(el.style.width).toBe('200px')
  })

  it('displays duration label', () => {
    const clip = makeClip({ timeline_start: 1, timeline_end: 4 })
    render(
      <TimelineClip clip={clip} zoom={1} scrollOffset={0} isSelected={false} onSelect={vi.fn()} />,
    )

    expect(screen.getByTestId('clip-duration-clip-1').textContent).toBe('3.0s')
  })

  it('calls onSelect when clicked', () => {
    const onSelect = vi.fn()
    const clip = makeClip()
    render(
      <TimelineClip clip={clip} zoom={1} scrollOffset={0} isSelected={false} onSelect={onSelect} />,
    )

    fireEvent.click(screen.getByTestId('clip-clip-1'))
    expect(onSelect).toHaveBeenCalledWith('clip-1')
  })

  it('shows selected styling when isSelected is true', () => {
    const clip = makeClip()
    render(
      <TimelineClip clip={clip} zoom={1} scrollOffset={0} isSelected={true} onSelect={vi.fn()} />,
    )

    const el = screen.getByTestId('clip-clip-1')
    expect(el.className).toContain('border-blue-400')
    expect(el.getAttribute('aria-selected')).toBe('true')
  })

  it('shows unselected styling when isSelected is false', () => {
    const clip = makeClip()
    render(
      <TimelineClip clip={clip} zoom={1} scrollOffset={0} isSelected={false} onSelect={vi.fn()} />,
    )

    const el = screen.getByTestId('clip-clip-1')
    expect(el.className).toContain('border-gray-600')
    expect(el.getAttribute('aria-selected')).toBe('false')
  })

  it('handles keyboard selection with Enter', () => {
    const onSelect = vi.fn()
    const clip = makeClip()
    render(
      <TimelineClip clip={clip} zoom={1} scrollOffset={0} isSelected={false} onSelect={onSelect} />,
    )

    fireEvent.keyDown(screen.getByTestId('clip-clip-1'), { key: 'Enter' })
    expect(onSelect).toHaveBeenCalledWith('clip-1')
  })

  it('uses in_point/out_point for duration when timeline_start/end are null', () => {
    const clip = makeClip({ timeline_start: null, timeline_end: null, in_point: 5, out_point: 8 })
    render(
      <TimelineClip clip={clip} zoom={1} scrollOffset={0} isSelected={false} onSelect={vi.fn()} />,
    )

    expect(screen.getByTestId('clip-duration-clip-1').textContent).toBe('3.0s')
  })

  it('renders multiple clips without overlap on same track', () => {
    const clip1 = makeClip({ id: 'c1', timeline_start: 0, timeline_end: 2 })
    const clip2 = makeClip({ id: 'c2', timeline_start: 2, timeline_end: 5 })

    render(
      <div style={{ position: 'relative' }}>
        <TimelineClip clip={clip1} zoom={1} scrollOffset={0} isSelected={false} onSelect={vi.fn()} />
        <TimelineClip clip={clip2} zoom={1} scrollOffset={0} isSelected={false} onSelect={vi.fn()} />
      </div>,
    )

    const el1 = screen.getByTestId('clip-c1')
    const el2 = screen.getByTestId('clip-c2')

    // clip1: left=0, width=200. clip2: left=200, width=300
    // No overlap: clip1 ends at 200, clip2 starts at 200
    const el1Right = parseFloat(el1.style.left) + parseFloat(el1.style.width)
    const el2Left = parseFloat(el2.style.left)
    expect(el2Left).toBeGreaterThanOrEqual(el1Right)
  })
})
