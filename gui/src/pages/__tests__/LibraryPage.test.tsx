import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import LibraryPage from '../LibraryPage'

vi.mock('../../hooks/useVideos', () => ({
  useVideos: vi.fn().mockReturnValue({
    videos: [],
    total: 0,
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
}))

beforeEach(() => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response('{}', { status: 404 }),
  )
})

function renderPage() {
  return render(
    <MemoryRouter>
      <LibraryPage />
    </MemoryRouter>,
  )
}

describe('LibraryPage', () => {
  it('renders with role="main" and id="main-content"', () => {
    renderPage()
    const main = screen.getByRole('main')
    expect(main).toHaveAttribute('id', 'main-content')
  })

  it('renders library heading', () => {
    renderPage()
    expect(screen.getByText('Library')).toBeDefined()
  })
})
