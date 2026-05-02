import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import EffectsPage from '../EffectsPage'

vi.mock('../../hooks/useEffects', () => ({
  useEffects: vi.fn().mockReturnValue({ effects: [], loading: false, error: null, refetch: vi.fn() }),
  deriveCategory: vi.fn().mockReturnValue('video'),
}))

vi.mock('../../hooks/useProjects', () => ({
  useProjects: vi.fn().mockReturnValue({ projects: [], total: 0, loading: false, error: null, refetch: vi.fn() }),
  fetchClips: vi.fn().mockResolvedValue({ clips: [], total: 0 }),
}))

vi.mock('../../hooks/useEffectPreview', () => ({
  useEffectPreview: vi.fn(),
}))

beforeEach(() => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response('{}', { status: 404 }),
  )
})

function renderPage() {
  return render(
    <MemoryRouter>
      <EffectsPage />
    </MemoryRouter>,
  )
}

describe('EffectsPage', () => {
  it('renders with role="main" and id="main-content"', () => {
    renderPage()
    const main = screen.getByRole('main')
    expect(main).toHaveAttribute('id', 'main-content')
  })

  it('renders effects heading', () => {
    renderPage()
    expect(screen.getByRole('heading', { name: 'Effects' })).toBeDefined()
  })
})
