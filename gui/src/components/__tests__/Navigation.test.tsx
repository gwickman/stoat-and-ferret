import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import Navigation from '../Navigation'

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('Navigation', () => {
  it('renders tabs when backend endpoints are available', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('', { status: 200 }),
    )

    render(
      <MemoryRouter>
        <Navigation />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('nav-tab-dashboard')).toBeDefined()
      expect(screen.getByTestId('nav-tab-library')).toBeDefined()
      expect(screen.getByTestId('nav-tab-projects')).toBeDefined()
    })
  })

  it('hides tabs when backend endpoints are unavailable', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Network error'))

    render(
      <MemoryRouter>
        <Navigation />
      </MemoryRouter>,
    )

    // Wait for fetch promises to settle
    await waitFor(() => {
      expect(screen.queryByTestId('nav-tab-dashboard')).toBeNull()
      expect(screen.queryByTestId('nav-tab-library')).toBeNull()
      expect(screen.queryByTestId('nav-tab-projects')).toBeNull()
    })
  })

  it('shows only available tabs when some endpoints fail', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = typeof input === 'string' ? input : (input as Request).url
      if (url.includes('/health/live')) {
        return new Response('', { status: 200 })
      }
      throw new Error('Network error')
    })

    render(
      <MemoryRouter>
        <Navigation />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('nav-tab-dashboard')).toBeDefined()
    })
    expect(screen.queryByTestId('nav-tab-library')).toBeNull()
    expect(screen.queryByTestId('nav-tab-projects')).toBeNull()
  })

  it('shows tabs when endpoint returns 405 (Method Not Allowed)', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('', { status: 405 }),
    )

    render(
      <MemoryRouter>
        <Navigation />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('nav-tab-dashboard')).toBeDefined()
    })
  })
})
