import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import VideoGrid from '../VideoGrid'
import type { Video } from '../../hooks/useVideos'

function makeVideo(overrides: Partial<Video> = {}): Video {
  return {
    id: 'v1',
    path: '/videos/test.mp4',
    filename: 'test.mp4',
    duration_frames: 750,
    frame_rate_numerator: 30,
    frame_rate_denominator: 1,
    width: 1920,
    height: 1080,
    video_codec: 'h264',
    audio_codec: 'aac',
    file_size: 1024000,
    thumbnail_path: '/thumbs/v1.jpg',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('VideoGrid', () => {
  it('renders video cards with thumbnails, filenames, and durations', () => {
    const videos = [
      makeVideo({ id: 'v1', filename: 'clip1.mp4', duration_frames: 1800 }),
      makeVideo({ id: 'v2', filename: 'clip2.mp4', duration_frames: 900 }),
    ]

    render(<VideoGrid videos={videos} loading={false} error={null} />)

    expect(screen.getByTestId('video-grid')).toBeDefined()
    expect(screen.getByTestId('video-card-v1')).toBeDefined()
    expect(screen.getByTestId('video-card-v2')).toBeDefined()

    expect(screen.getByTestId('video-filename-v1').textContent).toBe(
      'clip1.mp4',
    )
    expect(screen.getByTestId('video-filename-v2').textContent).toBe(
      'clip2.mp4',
    )

    expect(screen.getByTestId('video-duration-v1').textContent).toBe('1:00')
    expect(screen.getByTestId('video-duration-v2').textContent).toBe('0:30')

    const thumb = screen.getByTestId('video-thumbnail-v1') as HTMLImageElement
    expect(thumb.src).toContain('/api/v1/videos/v1/thumbnail')
  })

  it('shows loading state', () => {
    render(<VideoGrid videos={[]} loading={true} error={null} />)

    expect(screen.getByTestId('video-grid-loading')).toBeDefined()
    expect(screen.getByTestId('video-grid-loading').textContent).toBe(
      'Loading videos...',
    )
  })

  it('shows error state', () => {
    render(
      <VideoGrid videos={[]} loading={false} error="Fetch failed: 500" />,
    )

    expect(screen.getByTestId('video-grid-error')).toBeDefined()
    expect(screen.getByTestId('video-grid-error').textContent).toBe(
      'Fetch failed: 500',
    )
  })

  it('shows empty state when no videos', () => {
    render(<VideoGrid videos={[]} loading={false} error={null} />)

    expect(screen.getByTestId('video-grid-empty')).toBeDefined()
  })
})
