import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import ProjectsPage from '../ProjectsPage'

vi.mock('../../hooks/useProjects', () => ({
  useProjects: vi.fn().mockReturnValue({ projects: [], total: 0, loading: false, error: null, refetch: vi.fn() }),
  fetchClips: vi.fn().mockResolvedValue({ clips: [], total: 0 }),
}))

beforeEach(() => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response('{}', { status: 404 }),
  )
})

function renderPage() {
  return render(
    <MemoryRouter>
      <ProjectsPage />
    </MemoryRouter>,
  )
}

describe('ProjectsPage', () => {
  it('renders with role="main" and id="main-content"', () => {
    renderPage()
    const main = screen.getByRole('main')
    expect(main).toHaveAttribute('id', 'main-content')
  })

  it('renders projects heading', () => {
    renderPage()
    expect(screen.getByText('Projects')).toBeDefined()
  })
})
