import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import TimelinePage from '../../pages/TimelinePage'
import { useTimelineStore } from '../../stores/timelineStore'
import { useComposeStore } from '../../stores/composeStore'
import { useProjectStore } from '../../stores/projectStore'

vi.mock('../../components/render/StartRenderModal', () => ({
  default: ({ open, onClose, onSubmitted }: { open: boolean; onClose: () => void; onSubmitted: () => void }) => {
    if (!open) return null
    return (
      <div data-testid="start-render-modal">
        <button data-testid="modal-close" onClick={onClose}>Close</button>
        <button data-testid="modal-submit" onClick={onSubmitted}>Submit</button>
      </div>
    )
  },
}))

const mockPresets = {
  presets: [
    {
      name: 'PipTopLeft',
      description: 'Picture-in-picture top-left',
      ai_hint: 'Use for commentary',
      min_inputs: 2,
      max_inputs: 2,
    },
  ],
  total: 1,
}

const mockEmptyProjects = { projects: [], total: 0 }

const mockEmptyTimeline = { tracks: [], duration: 0, version: 0 }

/** Return the right mock response per API endpoint, with a fresh Response each call. */
function mockFetchForEndpoints(
  overrides: Record<string, unknown> = {},
) {
  const responses: Record<string, unknown> = {
    '/api/v1/compose/presets': mockPresets,
    ...overrides,
  }
  return vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    const url = typeof input === 'string' ? input : input instanceof Request ? input.url : String(input)
    for (const [pattern, body] of Object.entries(responses)) {
      if (url.includes(pattern)) {
        return Promise.resolve(
          new Response(JSON.stringify(body), { status: 200 }),
        )
      }
    }
    // Default: empty projects response for any unmatched URL (e.g. /api/v1/projects)
    return Promise.resolve(
      new Response(JSON.stringify(mockEmptyProjects), { status: 200 }),
    )
  })
}

beforeEach(() => {
  vi.restoreAllMocks()
  useTimelineStore.getState().reset()
  useComposeStore.getState().reset()
  useProjectStore.setState({ selectedProjectId: null })
})

function renderTimelinePage(initialPath = '/timeline') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/timeline" element={<TimelinePage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('TimelinePage', () => {
  it('renders the page with heading', async () => {
    mockFetchForEndpoints()

    renderTimelinePage()

    expect(screen.getByText('Timeline')).toBeDefined()
    expect(screen.getByTestId('timeline-page')).toBeDefined()
  })

  it('renders with role="main" and id="main-content"', () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => {}))

    renderTimelinePage()

    const main = screen.getByRole('main')
    expect(main).toHaveAttribute('id', 'main-content')
  })

  it('shows loading state while fetching', () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => {}))

    renderTimelinePage()

    expect(screen.getByTestId('timeline-loading')).toBeDefined()
  })

  it('shows empty state when no data', async () => {
    mockFetchForEndpoints({
      '/api/v1/compose/presets': { presets: [], total: 0 },
    })

    renderTimelinePage()

    await waitFor(() => {
      expect(screen.getByTestId('timeline-empty')).toBeDefined()
    })
  })

  it('shows error state on fetch failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Network error'))

    renderTimelinePage()

    await waitFor(() => {
      expect(screen.getByTestId('timeline-error')).toBeDefined()
      expect(screen.getByText('Network error')).toBeDefined()
    })
  })

  it('renders presets when loaded', async () => {
    mockFetchForEndpoints()

    renderTimelinePage()

    await waitFor(() => {
      expect(screen.getByTestId('timeline-presets')).toBeDefined()
    })
    expect(screen.getByText(/PipTopLeft/)).toBeDefined()
  })

  it('renders tracks when timeline data is pre-loaded', async () => {
    mockFetchForEndpoints()

    useTimelineStore.setState({
      tracks: [
        {
          id: 'track-1',
          project_id: 'proj-1',
          track_type: 'video',
          label: 'Video 1',
          z_index: 0,
          muted: false,
          locked: false,
          clips: [],
        },
      ],
      duration: 5.0,
      version: 1,
    })

    renderTimelinePage()

    await waitFor(() => {
      expect(screen.getByTestId('timeline-tracks')).toBeDefined()
    })
    expect(screen.getByText(/Video 1/)).toBeDefined()
  })

  it('is accessible at /timeline route', () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => {}))

    renderTimelinePage('/timeline')

    expect(screen.getByTestId('timeline-page')).toBeDefined()
  })

  describe('Start Render button', () => {
    it('renders in header adjacent to heading', async () => {
      mockFetchForEndpoints({ '/api/v1/projects/test-project-id/timeline': mockEmptyTimeline })
      useProjectStore.setState({ selectedProjectId: 'test-project-id' })

      renderTimelinePage()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Start Render' })).toBeDefined()
      })
      // Button and heading share the same flex container
      const button = screen.getByRole('button', { name: 'Start Render' })
      const heading = screen.getByText('Timeline')
      expect(button.parentElement).toBe(heading.parentElement)
    })

    it('opens modal on click', async () => {
      mockFetchForEndpoints({ '/api/v1/projects/test-project-id/timeline': mockEmptyTimeline })
      useProjectStore.setState({ selectedProjectId: 'test-project-id' })

      renderTimelinePage()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Start Render' })).toBeDefined()
      })

      fireEvent.click(screen.getByRole('button', { name: 'Start Render' }))

      expect(screen.getByTestId('start-render-modal')).toBeDefined()
    })

    it('is disabled when selectedProjectId is null', async () => {
      mockFetchForEndpoints()
      useProjectStore.setState({ selectedProjectId: null })

      renderTimelinePage()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Start Render' })).toBeDefined()
      })

      const button = screen.getByRole('button', { name: 'Start Render' }) as HTMLButtonElement
      expect(button.disabled).toBe(true)
    })

    it('shows tooltip when disabled', async () => {
      mockFetchForEndpoints()
      useProjectStore.setState({ selectedProjectId: null })

      renderTimelinePage()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Start Render' })).toBeDefined()
      })

      const button = screen.getByRole('button', { name: 'Start Render' })
      expect(button.getAttribute('title')).toBe('Select a project first')
    })

    it('closes modal via onClose callback', async () => {
      mockFetchForEndpoints({ '/api/v1/projects/test-project-id/timeline': mockEmptyTimeline })
      useProjectStore.setState({ selectedProjectId: 'test-project-id' })

      renderTimelinePage()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Start Render' })).toBeDefined()
      })

      fireEvent.click(screen.getByRole('button', { name: 'Start Render' }))
      expect(screen.getByTestId('start-render-modal')).toBeDefined()

      fireEvent.click(screen.getByTestId('modal-close'))
      expect(screen.queryByTestId('start-render-modal')).toBeNull()
    })

    it('onSubmitted is a no-op', async () => {
      mockFetchForEndpoints({ '/api/v1/projects/test-project-id/timeline': mockEmptyTimeline })
      useProjectStore.setState({ selectedProjectId: 'test-project-id' })

      renderTimelinePage()

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Start Render' })).toBeDefined()
      })

      fireEvent.click(screen.getByRole('button', { name: 'Start Render' }))
      // Clicking submit should not throw or cause side effects
      fireEvent.click(screen.getByTestId('modal-submit'))
      // Modal still open (onSubmitted doesn't close it)
      expect(screen.getByTestId('start-render-modal')).toBeDefined()
    })
  })
})
