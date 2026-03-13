import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import TimelineCanvas from '../TimelineCanvas'
import type { Track } from '../../types/timeline'

const makeTracks = (count: number): Track[] =>
  Array.from({ length: count }, (_, i) => ({
    id: `track-${i}`,
    project_id: 'proj-1',
    track_type: i === 0 ? 'video' : 'audio',
    label: `Track ${i}`,
    z_index: i,
    muted: false,
    locked: false,
    clips: [],
  }))

describe('TimelineCanvas', () => {
  it('renders canvas with tracks', () => {
    render(<TimelineCanvas tracks={makeTracks(2)} duration={10} />)

    expect(screen.getByTestId('timeline-canvas')).toBeDefined()
    expect(screen.getByTestId('canvas-tracks')).toBeDefined()
    expect(screen.getByTestId('track-track-0')).toBeDefined()
    expect(screen.getByTestId('track-track-1')).toBeDefined()
  })

  it('renders empty state when no tracks', () => {
    render(<TimelineCanvas tracks={[]} duration={0} />)

    expect(screen.getByTestId('timeline-canvas-empty')).toBeDefined()
    expect(screen.getByText('No tracks on the timeline. Add clips to get started.')).toBeDefined()
  })

  it('shows duration', () => {
    render(<TimelineCanvas tracks={makeTracks(1)} duration={15.5} />)

    expect(screen.getByTestId('canvas-duration').textContent).toContain('15.5s')
  })

  it('includes zoom controls', () => {
    render(<TimelineCanvas tracks={makeTracks(1)} duration={10} />)

    expect(screen.getByTestId('zoom-controls')).toBeDefined()
  })

  it('includes time ruler', () => {
    render(<TimelineCanvas tracks={makeTracks(1)} duration={10} />)

    expect(screen.getByTestId('time-ruler')).toBeDefined()
  })

  it('zoom in increases zoom percentage', () => {
    render(<TimelineCanvas tracks={makeTracks(1)} duration={10} />)

    // Default zoom is 100%
    expect(screen.getByTestId('zoom-reset').textContent).toBe('100%')

    fireEvent.click(screen.getByTestId('zoom-in'))
    expect(screen.getByTestId('zoom-reset').textContent).toBe('125%')
  })

  it('zoom out decreases zoom percentage', () => {
    render(<TimelineCanvas tracks={makeTracks(1)} duration={10} />)

    fireEvent.click(screen.getByTestId('zoom-out'))
    expect(screen.getByTestId('zoom-reset').textContent).toBe('75%')
  })

  it('zoom reset returns to 100%', () => {
    render(<TimelineCanvas tracks={makeTracks(1)} duration={10} />)

    fireEvent.click(screen.getByTestId('zoom-in'))
    fireEvent.click(screen.getByTestId('zoom-in'))
    expect(screen.getByTestId('zoom-reset').textContent).toBe('150%')

    fireEvent.click(screen.getByTestId('zoom-reset'))
    expect(screen.getByTestId('zoom-reset').textContent).toBe('100%')
  })

  it('renders tracks sorted by z_index', () => {
    const tracks: Track[] = [
      { ...makeTracks(1)[0], id: 'high', z_index: 10, label: 'Top' },
      { ...makeTracks(1)[0], id: 'low', z_index: 0, label: 'Bottom' },
      { ...makeTracks(1)[0], id: 'mid', z_index: 5, label: 'Middle' },
    ]
    render(<TimelineCanvas tracks={tracks} duration={10} />)

    const trackArea = screen.getByTestId('canvas-tracks')
    const trackElements = trackArea.children
    // Should be sorted: z_index 0, 5, 10
    expect(trackElements[0].getAttribute('data-testid')).toBe('track-low')
    expect(trackElements[1].getAttribute('data-testid')).toBe('track-mid')
    expect(trackElements[2].getAttribute('data-testid')).toBe('track-high')
  })

  it('has scrollable area', () => {
    render(<TimelineCanvas tracks={makeTracks(1)} duration={10} />)

    expect(screen.getByTestId('canvas-scroll-area')).toBeDefined()
  })
})
