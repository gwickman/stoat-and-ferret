import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import RenderJobCard from '../RenderJobCard'
import { useRenderStore } from '../../../stores/renderStore'
import type { RenderJob } from '../../../stores/renderStore'

function makeJob(overrides: Partial<RenderJob> = {}): RenderJob {
  return {
    id: 'job-1',
    project_id: 'proj-1',
    status: 'running',
    output_path: '/out/video.mp4',
    output_format: 'mp4',
    quality_preset: 'standard',
    progress: 0.5,
    eta_seconds: null,
    speed_ratio: null,
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
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{}', { status: 200 }))
})

describe('RenderJobCard', () => {
  // --- Progress bar ---

  it('renders progress bar width matching job.progress * 100%', () => {
    render(<RenderJobCard job={makeJob({ progress: 0.75 })} />)
    const fill = screen.getByTestId('progress-bar-fill')
    expect(fill.style.width).toBe('75%')
  })

  it('clamps progress bar at 100%', () => {
    render(<RenderJobCard job={makeJob({ progress: 1.05 })} />)
    const fill = screen.getByTestId('progress-bar-fill')
    expect(fill.style.width).toBe('100%')
  })

  // --- ETA ---

  it('shows formatted ETA when eta_seconds is present', () => {
    render(<RenderJobCard job={makeJob({ eta_seconds: 125 })} />)
    const eta = screen.getByTestId('eta-text')
    expect(eta.textContent).toBe('ETA 2m 5s')
  })

  it('shows ETA in seconds when under 60', () => {
    render(<RenderJobCard job={makeJob({ eta_seconds: 45 })} />)
    const eta = screen.getByTestId('eta-text')
    expect(eta.textContent).toBe('ETA 45s')
  })

  it('hides ETA when eta_seconds is null', () => {
    render(<RenderJobCard job={makeJob({ eta_seconds: null })} />)
    expect(screen.queryByTestId('eta-text')).toBeNull()
  })

  // --- Speed ratio ---

  it('shows speed ratio as "N.Nx real-time"', () => {
    render(<RenderJobCard job={makeJob({ speed_ratio: 2.3 })} />)
    const speed = screen.getByTestId('speed-text')
    expect(speed.textContent).toBe('2.3x real-time')
  })

  it('hides speed ratio when speed_ratio is null', () => {
    render(<RenderJobCard job={makeJob({ speed_ratio: null })} />)
    expect(screen.queryByTestId('speed-text')).toBeNull()
  })

  // --- StatusBadge ---

  it('shows StatusBadge with correct status', () => {
    render(<RenderJobCard job={makeJob({ status: 'failed' })} />)
    expect(screen.getByTestId('status-badge-label').textContent).toBe('Failed')
  })

  // --- Cancel button ---

  it('enables cancel button for queued status', () => {
    render(<RenderJobCard job={makeJob({ status: 'queued' })} />)
    const btn = screen.getByTestId('cancel-btn') as HTMLButtonElement
    expect(btn.disabled).toBe(false)
  })

  it('enables cancel button for running status', () => {
    render(<RenderJobCard job={makeJob({ status: 'running' })} />)
    const btn = screen.getByTestId('cancel-btn') as HTMLButtonElement
    expect(btn.disabled).toBe(false)
  })

  it('disables cancel button for completed status', () => {
    render(<RenderJobCard job={makeJob({ status: 'completed' })} />)
    const btn = screen.getByTestId('cancel-btn') as HTMLButtonElement
    expect(btn.disabled).toBe(true)
  })

  it('disables cancel button for failed status', () => {
    render(<RenderJobCard job={makeJob({ status: 'failed' })} />)
    const btn = screen.getByTestId('cancel-btn') as HTMLButtonElement
    expect(btn.disabled).toBe(true)
  })

  it('disables cancel button for cancelled status', () => {
    render(<RenderJobCard job={makeJob({ status: 'cancelled' })} />)
    const btn = screen.getByTestId('cancel-btn') as HTMLButtonElement
    expect(btn.disabled).toBe(true)
  })

  // --- Retry button ---

  it('enables retry button for failed status', () => {
    render(<RenderJobCard job={makeJob({ status: 'failed' })} />)
    const btn = screen.getByTestId('retry-btn') as HTMLButtonElement
    expect(btn.disabled).toBe(false)
  })

  it('disables retry button for running status', () => {
    render(<RenderJobCard job={makeJob({ status: 'running' })} />)
    const btn = screen.getByTestId('retry-btn') as HTMLButtonElement
    expect(btn.disabled).toBe(true)
  })

  it('disables retry button for completed status', () => {
    render(<RenderJobCard job={makeJob({ status: 'completed' })} />)
    const btn = screen.getByTestId('retry-btn') as HTMLButtonElement
    expect(btn.disabled).toBe(true)
  })

  // --- Retry 409 handling ---

  it('shows error and disables retry on 409 response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Retry limit reached' }), { status: 409 }),
    )

    render(<RenderJobCard job={makeJob({ status: 'failed' })} />)
    fireEvent.click(screen.getByTestId('retry-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('retry-error').textContent).toBe('Retry limit reached')
    })
    const btn = screen.getByTestId('retry-btn') as HTMLButtonElement
    expect(btn.disabled).toBe(true)
  })

  // --- Delete button ---

  it('delete button is always enabled', () => {
    for (const status of ['queued', 'running', 'completed', 'failed', 'cancelled']) {
      const { unmount } = render(<RenderJobCard job={makeJob({ status })} />)
      const btn = screen.getByTestId('delete-btn') as HTMLButtonElement
      expect(btn.disabled).toBe(false)
      unmount()
    }
  })

  // --- Action button API calls ---

  it('cancel button calls POST /render/{id}/cancel', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('{}', { status: 200 }),
    )

    render(<RenderJobCard job={makeJob({ id: 'r-42', status: 'running' })} />)
    fireEvent.click(screen.getByTestId('cancel-btn'))

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith('/api/v1/render/r-42/cancel', { method: 'POST' })
    })
  })

  it('retry button calls POST /render/{id}/retry', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('{}', { status: 200 }),
    )

    render(<RenderJobCard job={makeJob({ id: 'r-42', status: 'failed' })} />)
    fireEvent.click(screen.getByTestId('retry-btn'))

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith('/api/v1/render/r-42/retry', { method: 'POST' })
    })
  })

  it('delete button calls DELETE /render/{id} after confirmation', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('{}', { status: 200 }),
    )

    render(<RenderJobCard job={makeJob({ id: 'r-42', status: 'completed' })} />)
    fireEvent.click(screen.getByTestId('delete-btn'))

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith('/api/v1/render/r-42', { method: 'DELETE' })
    })
  })

  it('delete button does not call API when confirmation denied', () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const fetchSpy = vi.spyOn(globalThis, 'fetch')

    render(<RenderJobCard job={makeJob({ id: 'r-42', status: 'completed' })} />)
    fireEvent.click(screen.getByTestId('delete-btn'))

    expect(fetchSpy).not.toHaveBeenCalledWith('/api/v1/render/r-42', { method: 'DELETE' })
  })

  // --- data-testid ---

  it('renders with correct data-testid', () => {
    render(<RenderJobCard job={makeJob({ id: 'abc-123' })} />)
    expect(screen.getByTestId('render-job-card-abc-123')).toBeDefined()
  })

  // --- Loading states ---

  it('cancel button is disabled while cancel request is in-flight', async () => {
    let resolveFetch!: () => void
    const okResponse = new Response('{}', { status: 200 })
    vi.spyOn(globalThis, 'fetch').mockImplementationOnce(
      () => new Promise<Response>((res) => { resolveFetch = () => res(okResponse) }),
    )

    render(<RenderJobCard job={makeJob({ status: 'running' })} />)
    fireEvent.click(screen.getByTestId('cancel-btn'))

    expect((screen.getByTestId('cancel-btn') as HTMLButtonElement).disabled).toBe(true)

    resolveFetch()
    await waitFor(() =>
      expect((screen.getByTestId('cancel-btn') as HTMLButtonElement).disabled).toBe(false),
    )
  })

  it('retry button is disabled while retry request is in-flight', async () => {
    let resolveFetch!: () => void
    const okResponse = new Response('{}', { status: 200 })
    vi.spyOn(globalThis, 'fetch').mockImplementationOnce(
      () => new Promise<Response>((res) => { resolveFetch = () => res(okResponse) }),
    )

    render(<RenderJobCard job={makeJob({ status: 'failed' })} />)
    fireEvent.click(screen.getByTestId('retry-btn'))

    expect((screen.getByTestId('retry-btn') as HTMLButtonElement).disabled).toBe(true)

    resolveFetch()
    await waitFor(() =>
      expect((screen.getByTestId('retry-btn') as HTMLButtonElement).disabled).toBe(false),
    )
  })

  it('delete button is disabled while delete request is in-flight', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    let resolveFetch!: () => void
    const okResponse = new Response('{}', { status: 200 })
    vi.spyOn(globalThis, 'fetch').mockImplementationOnce(
      () => new Promise<Response>((res) => { resolveFetch = () => res(okResponse) }),
    )

    render(<RenderJobCard job={makeJob({ status: 'completed' })} />)
    fireEvent.click(screen.getByTestId('delete-btn'))

    expect((screen.getByTestId('delete-btn') as HTMLButtonElement).disabled).toBe(true)

    resolveFetch()
    await waitFor(() =>
      expect((screen.getByTestId('delete-btn') as HTMLButtonElement).disabled).toBe(false),
    )
  })
})
