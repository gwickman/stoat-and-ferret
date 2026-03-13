import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import Track from '../Track'
import type { Track as TrackType } from '../../types/timeline'

const noop = vi.fn()

const makeTrack = (overrides: Partial<TrackType> = {}): TrackType => ({
  id: 'track-1',
  project_id: 'proj-1',
  track_type: 'video',
  label: 'Video 1',
  z_index: 0,
  muted: false,
  locked: false,
  clips: [],
  ...overrides,
})

describe('Track', () => {
  it('renders with label', () => {
    render(<Track track={makeTrack()} zoom={1} scrollOffset={0} selectedClipId={null} onSelectClip={noop} />)

    expect(screen.getByTestId('track-track-1')).toBeDefined()
    expect(screen.getByTestId('track-label-track-1').textContent).toContain('Video 1')
  })

  it('renders content area', () => {
    render(<Track track={makeTrack()} zoom={1} scrollOffset={0} selectedClipId={null} onSelectClip={noop} />)

    expect(screen.getByTestId('track-content-track-1')).toBeDefined()
  })

  it('shows muted indicator when muted', () => {
    render(<Track track={makeTrack({ muted: true })} zoom={1} scrollOffset={0} selectedClipId={null} onSelectClip={noop} />)

    expect(screen.getByTestId('track-muted-track-1')).toBeDefined()
  })

  it('does not show muted indicator when not muted', () => {
    render(<Track track={makeTrack({ muted: false })} zoom={1} scrollOffset={0} selectedClipId={null} onSelectClip={noop} />)

    expect(screen.queryByTestId('track-muted-track-1')).toBeNull()
  })

  it('shows locked indicator when locked', () => {
    render(<Track track={makeTrack({ locked: true })} zoom={1} scrollOffset={0} selectedClipId={null} onSelectClip={noop} />)

    expect(screen.getByTestId('track-locked-track-1')).toBeDefined()
  })

  it('uses z_index for ordering', () => {
    render(
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <Track track={makeTrack({ id: 'a', z_index: 2 })} zoom={1} scrollOffset={0} selectedClipId={null} onSelectClip={noop} />
        <Track track={makeTrack({ id: 'b', z_index: 0 })} zoom={1} scrollOffset={0} selectedClipId={null} onSelectClip={noop} />
        <Track track={makeTrack({ id: 'c', z_index: 1 })} zoom={1} scrollOffset={0} selectedClipId={null} onSelectClip={noop} />
      </div>,
    )

    // All three tracks rendered
    expect(screen.getByTestId('track-a')).toBeDefined()
    expect(screen.getByTestId('track-b')).toBeDefined()
    expect(screen.getByTestId('track-c')).toBeDefined()
    // Verify z_index is applied via CSS order
    const trackA = screen.getByTestId('track-a')
    expect(trackA.style.order).toBe('2')
    const trackB = screen.getByTestId('track-b')
    expect(trackB.style.order).toBe('0')
  })
})
