import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ProjectDetails from '../ProjectDetails'
import type { Project } from '../../hooks/useProjects'

const mockProject: Project = {
  id: 'proj-1',
  name: 'My Film',
  output_width: 1920,
  output_height: 1080,
  output_fps: 30,
  created_at: '2025-01-15T10:00:00Z',
  updated_at: '2025-01-15T10:00:00Z',
}

const mockClips = [
  {
    id: 'clip-1',
    project_id: 'proj-1',
    source_video_id: 'vid-1',
    in_point: 0,
    out_point: 90,
    timeline_position: 0,
    created_at: '2025-01-15T10:00:00Z',
    updated_at: '2025-01-15T10:00:00Z',
  },
  {
    id: 'clip-2',
    project_id: 'proj-1',
    source_video_id: 'vid-2',
    in_point: 30,
    out_point: 150,
    timeline_position: 90,
    created_at: '2025-01-15T10:00:00Z',
    updated_at: '2025-01-15T10:00:00Z',
  },
]

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('ProjectDetails', () => {
  it('displays project name and metadata', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ clips: [], total: 0 }), { status: 200 }),
    )

    render(
      <ProjectDetails
        project={mockProject}
        onBack={vi.fn()}
        onDelete={vi.fn()}
      />,
    )

    expect(screen.getByTestId('project-detail-name').textContent).toBe('My Film')
    expect(screen.getByTestId('project-metadata').textContent).toContain(
      '1920x1080',
    )
    expect(screen.getByTestId('project-metadata').textContent).toContain(
      '30 fps',
    )
  })

  it('displays clip list with timeline positions', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(
        JSON.stringify({ clips: mockClips, total: 2 }),
        { status: 200 },
      ),
    )

    render(
      <ProjectDetails
        project={mockProject}
        onBack={vi.fn()}
        onDelete={vi.fn()}
      />,
    )

    await waitFor(() => {
      expect(screen.getByTestId('clips-table')).toBeDefined()
    })

    // Clip 1: timeline_position=0, in=0, out=90 at 30fps
    // 0 frames = 0:00.00, 90 frames = 0:03.00
    expect(screen.getByTestId('clip-position-clip-1').textContent).toBe('0:00.00')
    expect(screen.getByTestId('clip-in-clip-1').textContent).toBe('0:00.00')
    expect(screen.getByTestId('clip-out-clip-1').textContent).toBe('0:03.00')
    expect(screen.getByTestId('clip-duration-clip-1').textContent).toBe('0:03.00')

    // Clip 2: timeline_position=90, in=30, out=150 at 30fps
    // 90 frames = 0:03.00, 30 frames = 0:01.00, 150 frames = 0:05.00
    expect(screen.getByTestId('clip-position-clip-2').textContent).toBe('0:03.00')
    expect(screen.getByTestId('clip-in-clip-2').textContent).toBe('0:01.00')
    expect(screen.getByTestId('clip-out-clip-2').textContent).toBe('0:05.00')
    expect(screen.getByTestId('clip-duration-clip-2').textContent).toBe('0:04.00')
  })

  it('shows empty state when no clips', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ clips: [], total: 0 }), { status: 200 }),
    )

    render(
      <ProjectDetails
        project={mockProject}
        onBack={vi.fn()}
        onDelete={vi.fn()}
      />,
    )

    await waitFor(() => {
      expect(screen.getByTestId('clips-empty')).toBeDefined()
    })
  })

  it('shows error when clip fetch fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response('', { status: 500 }),
    )

    render(
      <ProjectDetails
        project={mockProject}
        onBack={vi.fn()}
        onDelete={vi.fn()}
      />,
    )

    await waitFor(() => {
      expect(screen.getByTestId('clips-error')).toBeDefined()
    })
  })
})
