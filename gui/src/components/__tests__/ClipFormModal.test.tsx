import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ClipFormModal from '../ClipFormModal'
import { useClipStore } from '../../stores/clipStore'
import type { Clip } from '../../hooks/useProjects'

const mockVideos = [
  {
    id: 'vid-1',
    path: '/videos/test1.mp4',
    filename: 'test1.mp4',
    duration_frames: 300,
    frame_rate_numerator: 30,
    frame_rate_denominator: 1,
    width: 1920,
    height: 1080,
    video_codec: 'h264',
    audio_codec: 'aac',
    file_size: 1000000,
    thumbnail_path: null,
    created_at: '2025-01-15T10:00:00Z',
    updated_at: '2025-01-15T10:00:00Z',
  },
  {
    id: 'vid-2',
    path: '/videos/test2.mp4',
    filename: 'test2.mp4',
    duration_frames: 600,
    frame_rate_numerator: 30,
    frame_rate_denominator: 1,
    width: 1920,
    height: 1080,
    video_codec: 'h264',
    audio_codec: null,
    file_size: 2000000,
    thumbnail_path: null,
    created_at: '2025-01-15T11:00:00Z',
    updated_at: '2025-01-15T11:00:00Z',
  },
]

const mockClip: Clip = {
  id: 'clip-1',
  project_id: 'proj-1',
  source_video_id: 'vid-1',
  in_point: 10,
  out_point: 90,
  timeline_position: 0,
  created_at: '2025-01-15T10:00:00Z',
  updated_at: '2025-01-15T10:00:00Z',
}

beforeEach(() => {
  vi.restoreAllMocks()
  useClipStore.getState().reset()
})

function mockFetchVideos() {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(
      JSON.stringify({ videos: mockVideos, total: 2, limit: 1000, offset: 0 }),
      { status: 200 },
    ),
  )
}

describe('ClipFormModal', () => {
  it('renders empty form for Add mode', async () => {
    mockFetchVideos()

    render(
      <ClipFormModal
        mode="add"
        projectId="proj-1"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    )

    expect(screen.getByTestId('clip-form-modal')).toBeDefined()
    // Title shows "Add Clip"
    expect(screen.getByTestId('clip-form-modal').textContent).toContain('Add Clip')
    expect(screen.getByTestId('select-source-video')).toBeDefined()
    expect(screen.getByTestId('input-in-point')).toBeDefined()
    expect(screen.getByTestId('input-out-point')).toBeDefined()
    expect(screen.getByTestId('input-timeline-position')).toBeDefined()

    // Fields should be empty (no pre-populated values)
    expect((screen.getByTestId('input-in-point') as HTMLInputElement).value).toBe('')
    expect((screen.getByTestId('input-out-point') as HTMLInputElement).value).toBe('')
    expect((screen.getByTestId('input-timeline-position') as HTMLInputElement).value).toBe('')
  })

  it('renders pre-populated form for Edit mode', () => {
    mockFetchVideos()

    render(
      <ClipFormModal
        mode="edit"
        clip={mockClip}
        projectId="proj-1"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    )

    expect(screen.getByText('Edit Clip')).toBeDefined()
    expect((screen.getByTestId('input-in-point') as HTMLInputElement).value).toBe('10')
    expect((screen.getByTestId('input-out-point') as HTMLInputElement).value).toBe('90')
    expect((screen.getByTestId('input-timeline-position') as HTMLInputElement).value).toBe('0')
    // Source video select should not appear in edit mode
    expect(screen.queryByTestId('select-source-video')).toBeNull()
  })

  it('validates required fields before submission', async () => {
    mockFetchVideos()

    render(
      <ClipFormModal
        mode="add"
        projectId="proj-1"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    )

    // Submit with empty fields
    fireEvent.click(screen.getByTestId('btn-clip-save'))

    await waitFor(() => {
      expect(screen.getByTestId('clip-form-error')).toBeDefined()
    })
  })

  it('displays backend validation errors', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
    // Videos fetch
    fetchSpy.mockResolvedValueOnce(
      new Response(
        JSON.stringify({ videos: mockVideos, total: 2, limit: 1000, offset: 0 }),
        { status: 200 },
      ),
    )

    render(
      <ClipFormModal
        mode="edit"
        clip={mockClip}
        projectId="proj-1"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    )

    // Mock the update to fail with backend error
    fetchSpy.mockResolvedValueOnce(
      new Response(
        JSON.stringify({ detail: 'out_point must be greater than in_point' }),
        { status: 422 },
      ),
    )
    // The refresh fetch after error won't be called since we throw

    fireEvent.click(screen.getByTestId('btn-clip-save'))

    await waitFor(() => {
      expect(screen.getByTestId('clip-form-error')).toBeDefined()
      expect(screen.getByTestId('clip-form-error').textContent).toContain(
        'out_point must be greater than in_point',
      )
    })
  })

  it('disables submit button during submission', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
    // Videos fetch
    fetchSpy.mockResolvedValueOnce(
      new Response(
        JSON.stringify({ videos: mockVideos, total: 2, limit: 1000, offset: 0 }),
        { status: 200 },
      ),
    )

    render(
      <ClipFormModal
        mode="edit"
        clip={mockClip}
        projectId="proj-1"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    )

    // Make the PATCH take a while by using a never-resolving promise
    let resolveUpdate: (value: Response) => void
    fetchSpy.mockReturnValueOnce(
      new Promise<Response>((resolve) => {
        resolveUpdate = resolve
      }),
    )

    fireEvent.click(screen.getByTestId('btn-clip-save'))

    await waitFor(() => {
      expect((screen.getByTestId('btn-clip-save') as HTMLButtonElement).disabled).toBe(true)
      expect(screen.getByTestId('btn-clip-save').textContent).toBe('Saving...')
    })

    // Clean up the pending promise
    resolveUpdate!(new Response(JSON.stringify(mockClip), { status: 200 }))
  })
})
