import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ProjectList from '../ProjectList'
import type { Project } from '../../hooks/useProjects'

const mockProjects: Project[] = [
  {
    id: 'proj-1',
    name: 'My Film',
    output_width: 1920,
    output_height: 1080,
    output_fps: 30,
    created_at: '2025-01-15T10:00:00Z',
    updated_at: '2025-01-15T10:00:00Z',
  },
  {
    id: 'proj-2',
    name: 'Short Video',
    output_width: 3840,
    output_height: 2160,
    output_fps: 60,
    created_at: '2025-02-01T14:30:00Z',
    updated_at: '2025-02-01T14:30:00Z',
  },
]

const clipCounts: Record<string, number> = {
  'proj-1': 5,
  'proj-2': 0,
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('ProjectList', () => {
  it('shows loading state', () => {
    render(
      <ProjectList
        projects={[]}
        clipCounts={{}}
        loading={true}
        error={null}
        onSelect={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    expect(screen.getByTestId('project-list-loading')).toBeDefined()
    expect(screen.getByTestId('project-list-loading').textContent).toBe(
      'Loading projects...',
    )
  })

  it('shows error state', () => {
    render(
      <ProjectList
        projects={[]}
        clipCounts={{}}
        loading={false}
        error="Network error"
        onSelect={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    expect(screen.getByTestId('project-list-error')).toBeDefined()
    expect(screen.getByTestId('project-list-error').textContent).toBe(
      'Network error',
    )
  })

  it('shows empty state', () => {
    render(
      <ProjectList
        projects={[]}
        clipCounts={{}}
        loading={false}
        error={null}
        onSelect={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    expect(screen.getByTestId('project-list-empty')).toBeDefined()
  })

  it('renders project cards with name, date, and clip count', () => {
    render(
      <ProjectList
        projects={mockProjects}
        clipCounts={clipCounts}
        loading={false}
        error={null}
        onSelect={vi.fn()}
        onDelete={vi.fn()}
      />,
    )

    expect(screen.getByTestId('project-list')).toBeDefined()

    // Project 1
    expect(screen.getByTestId('project-name-proj-1').textContent).toBe('My Film')
    expect(screen.getByTestId('project-date-proj-1').textContent).toContain('Jan')
    expect(screen.getByTestId('project-date-proj-1').textContent).toContain('2025')
    expect(screen.getByTestId('project-clips-proj-1').textContent).toBe('5 clips')

    // Project 2
    expect(screen.getByTestId('project-name-proj-2').textContent).toBe('Short Video')
    expect(screen.getByTestId('project-clips-proj-2').textContent).toBe('0 clips')
  })
})
