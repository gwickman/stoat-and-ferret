import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import TimelinePage from '../../pages/TimelinePage'
import { useTimelineStore } from '../../stores/timelineStore'
import { useComposeStore } from '../../stores/composeStore'

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

beforeEach(() => {
  vi.restoreAllMocks()
  useTimelineStore.getState().reset()
  useComposeStore.getState().reset()
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
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(mockPresets), { status: 200 }),
    )

    renderTimelinePage()

    expect(screen.getByText('Timeline')).toBeDefined()
    expect(screen.getByTestId('timeline-page')).toBeDefined()
  })

  it('shows loading state while fetching', () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => {}))

    renderTimelinePage()

    expect(screen.getByTestId('timeline-loading')).toBeDefined()
  })

  it('shows empty state when no data', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ presets: [], total: 0 }), { status: 200 }),
    )

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
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(mockPresets), { status: 200 }),
    )

    renderTimelinePage()

    await waitFor(() => {
      expect(screen.getByTestId('timeline-presets')).toBeDefined()
    })
    expect(screen.getByText(/PipTopLeft/)).toBeDefined()
  })

  it('renders tracks when timeline data is pre-loaded', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(mockPresets), { status: 200 }),
    )

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
})
