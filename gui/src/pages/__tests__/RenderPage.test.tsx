import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import RenderPage from '../RenderPage'
import { useRenderStore } from '../../stores/renderStore'
import type { RenderJob, QueueStatus } from '../../stores/renderStore'
import { useBatchStore } from '../../stores/batchStore'

// Mock useRenderEvents — it opens a real WebSocket; not needed for page tests
vi.mock('../../hooks/useRenderEvents', () => ({
  useRenderEvents: vi.fn(),
}))

const mockQueueStatus: QueueStatus = {
  active_count: 1,
  pending_count: 2,
  max_concurrent: 4,
  max_queue_depth: 20,
  disk_available_bytes: 500_000_000,
  disk_total_bytes: 1_000_000_000,
  completed_today: 5,
  failed_today: 1,
}

function makeJob(overrides: Partial<RenderJob> & { id: string; status: string }): RenderJob {
  return {
    project_id: 'proj-1',
    output_path: '/out/video.mp4',
    output_format: 'mp4',
    quality_preset: 'standard',
    progress: 0,
    eta_seconds: null,
    speed_ratio: null,
    frame_count: null,
    fps: null,
    encoder_name: null,
    encoder_type: null,
    error_message: null,
    retry_count: 0,
    created_at: '2025-06-01T00:00:00Z',
    updated_at: '2025-06-01T00:00:00Z',
    completed_at: null,
    ...overrides,
  }
}

beforeEach(() => {
  vi.restoreAllMocks()
  useRenderStore.getState().reset()
  useBatchStore.getState().reset()
  // Suppress fetch calls from useEffect
  vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('No mock'))
})

function mockFlags(batchRendering: boolean): void {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = typeof input === 'string' ? input : input.toString()
    if (url === '/api/v1/flags') {
      return new Response(
        JSON.stringify({
          testing_mode: false,
          seed_endpoint: false,
          synthetic_monitoring: false,
          batch_rendering: batchRendering,
        }),
        { status: 200 },
      )
    }
    if (url === '/api/v1/render') {
      return new Response(
        JSON.stringify({ items: [], total: 0, limit: 50, offset: 0 }),
        { status: 200 },
      )
    }
    if (url === '/api/v1/render/queue') {
      return new Response(JSON.stringify(mockQueueStatus), { status: 200 })
    }
    if (url === '/api/v1/render/encoders') {
      return new Response(
        JSON.stringify({ encoders: [], cached: false }),
        { status: 200 },
      )
    }
    if (url === '/api/v1/render/formats') {
      return new Response(JSON.stringify({ formats: [] }), { status: 200 })
    }
    return new Response('{}', { status: 200 })
  })
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/render']}>
      <RenderPage />
    </MemoryRouter>,
  )
}

describe('RenderPage', () => {
  it('renders with data-testid="render-page"', () => {
    renderPage()
    expect(screen.getByTestId('render-page')).toBeDefined()
    expect(screen.getByText('Render')).toBeDefined()
  })

  it('shows empty state when no jobs exist', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByTestId('empty-state')).toBeDefined()
    })
    expect(screen.getByText('No render jobs')).toBeDefined()
  })

  it('renders active jobs section with running jobs', () => {
    useRenderStore.setState({
      jobs: [makeJob({ id: 'j1', status: 'running', progress: 0.5 })],
    })
    renderPage()
    const section = screen.getByTestId('active-jobs-section')
    expect(section).toBeDefined()
    expect(section.textContent).toContain('j1')
    expect(section.textContent).toContain('Rendering')
    expect(section.textContent).toContain('50%')
  })

  it('renders pending jobs section with queued jobs', () => {
    useRenderStore.setState({
      jobs: [makeJob({ id: 'j2', status: 'queued' })],
    })
    renderPage()
    const section = screen.getByTestId('pending-jobs-section')
    expect(section).toBeDefined()
    expect(section.textContent).toContain('j2')
    expect(section.textContent).toContain('Queued')
  })

  it('renders completed jobs section with completed/failed/cancelled jobs', () => {
    useRenderStore.setState({
      jobs: [
        makeJob({ id: 'j3', status: 'completed' }),
        makeJob({ id: 'j4', status: 'failed' }),
        makeJob({ id: 'j5', status: 'cancelled' }),
      ],
    })
    renderPage()
    const section = screen.getByTestId('completed-jobs-section')
    expect(section).toBeDefined()
    expect(section.textContent).toContain('j3')
    expect(section.textContent).toContain('j4')
    expect(section.textContent).toContain('j5')
  })

  it('categorizes jobs into correct sections', () => {
    useRenderStore.setState({
      jobs: [
        makeJob({ id: 'active-1', status: 'running' }),
        makeJob({ id: 'pending-1', status: 'queued' }),
        makeJob({ id: 'done-1', status: 'completed' }),
      ],
    })
    renderPage()
    expect(screen.getByTestId('active-jobs-section').textContent).toContain('active-1')
    expect(screen.getByTestId('pending-jobs-section').textContent).toContain('pending-1')
    expect(screen.getByTestId('completed-jobs-section').textContent).toContain('done-1')
    // Verify they don't bleed across sections
    expect(screen.getByTestId('active-jobs-section').textContent).not.toContain('pending-1')
    expect(screen.getByTestId('pending-jobs-section').textContent).not.toContain('active-1')
  })

  it('shows queue status bar with counts', () => {
    useRenderStore.setState({ queueStatus: mockQueueStatus })
    renderPage()
    const bar = screen.getByTestId('queue-status-bar')
    expect(bar).toBeDefined()
    expect(bar.textContent).toContain('Active:')
    expect(bar.textContent).toContain('1')
    expect(bar.textContent).toContain('Pending:')
    expect(bar.textContent).toContain('2')
    expect(bar.textContent).toContain('Capacity:')
    expect(bar.textContent).toContain('4')
  })

  it('shows loading indicator when queue status is null and loading', () => {
    useRenderStore.setState({ queueStatus: null, isLoading: true })
    renderPage()
    const bar = screen.getByTestId('queue-status-bar')
    expect(bar.textContent).toContain('Loading queue status')
  })

  it('shows Start Render button that is visible and enabled', () => {
    renderPage()
    const btn = screen.getByTestId('start-render-btn')
    expect(btn).toBeDefined()
    expect(btn.textContent).toBe('Start Render')
    expect((btn as HTMLButtonElement).disabled).toBe(false)
  })

  it('has all required data-testid attributes', () => {
    useRenderStore.setState({
      jobs: [makeJob({ id: 'j1', status: 'running' })],
      queueStatus: mockQueueStatus,
    })
    renderPage()
    expect(screen.getByTestId('render-page')).toBeDefined()
    expect(screen.getByTestId('queue-status-bar')).toBeDefined()
    expect(screen.getByTestId('active-jobs-section')).toBeDefined()
    expect(screen.getByTestId('pending-jobs-section')).toBeDefined()
    expect(screen.getByTestId('completed-jobs-section')).toBeDefined()
    expect(screen.getByTestId('start-render-btn')).toBeDefined()
  })

  it('calls fetch actions on mount', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 0, limit: 50, offset: 0 }), { status: 200 }),
    )

    renderPage()

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith('/api/v1/render')
      expect(fetchSpy).toHaveBeenCalledWith('/api/v1/render/queue')
      expect(fetchSpy).toHaveBeenCalledWith('/api/v1/render/encoders')
      expect(fetchSpy).toHaveBeenCalledWith('/api/v1/render/formats')
    })
  })

  // ---- Batch tab tests (FR-004) ----

  it('renders the Render Queue tab and hides the Batch tab when flag is false', async () => {
    mockFlags(false)
    renderPage()
    expect(screen.getByTestId('render-tab-queue')).toBeDefined()
    await waitFor(() => {
      expect(screen.queryByTestId('render-tab-batch')).toBeNull()
    })
  })

  it('shows the Batch tab when batch_rendering flag is true', async () => {
    mockFlags(true)
    renderPage()
    await waitFor(() => {
      expect(screen.getByTestId('render-tab-batch')).toBeDefined()
    })
  })

  it('switching to the Batch tab renders BatchPanel and BatchJobList', async () => {
    mockFlags(true)
    renderPage()
    await waitFor(() => {
      expect(screen.getByTestId('render-tab-batch')).toBeDefined()
    })
    fireEvent.click(screen.getByTestId('render-tab-batch'))
    expect(screen.getByTestId('render-tab-batch-content')).toBeDefined()
    expect(screen.getByTestId('batch-panel')).toBeDefined()
    expect(screen.getByTestId('batch-job-list-section')).toBeDefined()
  })

  it('hides the Render Queue content when the Batch tab is active', async () => {
    mockFlags(true)
    renderPage()
    await waitFor(() => {
      expect(screen.getByTestId('render-tab-batch')).toBeDefined()
    })
    fireEvent.click(screen.getByTestId('render-tab-batch'))
    expect(screen.queryByTestId('render-tab-queue-content')).toBeNull()
    expect(screen.queryByTestId('start-render-btn')).toBeNull()
  })

  it('treats batch_rendering as false on flag fetch failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = typeof input === 'string' ? input : input.toString()
      if (url === '/api/v1/flags') {
        throw new Error('flags endpoint down')
      }
      return new Response(
        JSON.stringify({ items: [], total: 0, limit: 50, offset: 0 }),
        { status: 200 },
      )
    })
    renderPage()
    // Allow the failed fetch to settle.
    await new Promise((r) => setTimeout(r, 10))
    expect(screen.queryByTestId('render-tab-batch')).toBeNull()
  })

  it('treats missing batch_rendering field in flags response as false', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = typeof input === 'string' ? input : input.toString()
      if (url === '/api/v1/flags') {
        return new Response(
          JSON.stringify({ testing_mode: false, seed_endpoint: false }),
          { status: 200 },
        )
      }
      return new Response(
        JSON.stringify({ items: [], total: 0, limit: 50, offset: 0 }),
        { status: 200 },
      )
    })
    renderPage()
    await new Promise((r) => setTimeout(r, 10))
    expect(screen.queryByTestId('render-tab-batch')).toBeNull()
  })
})
