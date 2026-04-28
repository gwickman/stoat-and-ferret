import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import BatchJobList from '../BatchJobList'
import { useBatchStore, type BatchJob } from '../../../stores/batchStore'

function makeJob(overrides: Partial<BatchJob> & { job_id: string }): BatchJob {
  return {
    batch_id: 'b1',
    project_id: 'p1',
    status: 'queued',
    progress: 0,
    error: null,
    submitted_at: 1700000000000,
    ...overrides,
  }
}

beforeEach(() => {
  useBatchStore.getState().reset()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('BatchJobList', () => {
  it('shows an empty placeholder when there are no jobs', () => {
    render(<BatchJobList />)
    expect(screen.getByTestId('batch-job-list-empty')).toBeDefined()
  })

  it('renders a row per job in the store', () => {
    useBatchStore.getState().addJob(makeJob({ job_id: 'a', status: 'queued' }))
    useBatchStore.getState().addJob(makeJob({ job_id: 'b', status: 'running', progress: 0.4 }))
    render(<BatchJobList />)
    expect(screen.getByTestId('batch-job-row-a')).toBeDefined()
    expect(screen.getByTestId('batch-job-row-b')).toBeDefined()
  })

  it('filters jobs by batchId when provided', () => {
    useBatchStore.getState().addJob(makeJob({ job_id: 'a', batch_id: 'b1' }))
    useBatchStore.getState().addJob(makeJob({ job_id: 'b', batch_id: 'b2' }))
    render(<BatchJobList batchId="b1" />)
    expect(screen.getByTestId('batch-job-row-a')).toBeDefined()
    expect(screen.queryByTestId('batch-job-row-b')).toBeNull()
  })

  it('reflects job.progress as a percentage in the progress bar', () => {
    useBatchStore.getState().addJob(makeJob({ job_id: 'a', status: 'running', progress: 0.42 }))
    render(<BatchJobList />)
    expect(screen.getByTestId('batch-progress-pct-a').textContent).toBe('42%')
    const bar = screen.getByTestId('batch-progress-bar-a') as HTMLDivElement
    expect(bar.style.width).toBe('42%')
    expect(bar.getAttribute('aria-valuenow')).toBe('42')
  })

  it('clamps progress to [0, 100]', () => {
    useBatchStore.getState().addJob(makeJob({ job_id: 'a', status: 'running', progress: 1.5 }))
    render(<BatchJobList />)
    expect(screen.getByTestId('batch-progress-pct-a').textContent).toBe('100%')
  })

  it('shows the status badge text', () => {
    useBatchStore.getState().addJob(makeJob({ job_id: 'a', status: 'running' }))
    render(<BatchJobList />)
    expect(screen.getByTestId('batch-status-a').textContent).toBe('running')
  })

  it('hides the cancel button on terminal jobs', () => {
    useBatchStore.getState().addJob(makeJob({ job_id: 'done', status: 'completed', progress: 1 }))
    render(<BatchJobList />)
    expect(screen.queryByTestId('batch-cancel-done')).toBeNull()
  })

  it('shows the cancel button on queued and running jobs', () => {
    useBatchStore.getState().addJob(makeJob({ job_id: 'q', status: 'queued' }))
    useBatchStore.getState().addJob(makeJob({ job_id: 'r', status: 'running', progress: 0.5 }))
    render(<BatchJobList />)
    expect(screen.getByTestId('batch-cancel-q')).toBeDefined()
    expect(screen.getByTestId('batch-cancel-r')).toBeDefined()
  })

  it('issues DELETE and updates status to cancelled on 200', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          job_id: 'r',
          project_id: 'p',
          status: 'cancelled',
          progress: 0.5,
          error: null,
        }),
        { status: 200 },
      ),
    )
    useBatchStore.getState().addJob(makeJob({ job_id: 'r', status: 'running', progress: 0.5 }))
    render(<BatchJobList />)
    fireEvent.click(screen.getByTestId('batch-cancel-r'))
    await waitFor(() => {
      expect(useBatchStore.getState().jobs[0].status).toBe('cancelled')
    })
    expect(fetchSpy).toHaveBeenCalledWith('/api/v1/render/batch/r', { method: 'DELETE' })
  })

  it('removes the job and surfaces "Job not found" on 404', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('', { status: 404 }))
    useBatchStore.getState().addJob(makeJob({ job_id: 'r', status: 'running', progress: 0.5 }))
    render(<BatchJobList />)
    fireEvent.click(screen.getByTestId('batch-cancel-r'))
    await waitFor(() => {
      expect(useBatchStore.getState().jobs).toHaveLength(0)
    })
  })

  it('surfaces "Job already finished" on 409', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('', { status: 409 }))
    useBatchStore.getState().addJob(makeJob({ job_id: 'r', status: 'running', progress: 0.5 }))
    render(<BatchJobList />)
    fireEvent.click(screen.getByTestId('batch-cancel-r'))
    await waitFor(() => {
      expect(screen.getByTestId('batch-error-r').textContent).toContain('already finished')
    })
  })

  it('shows generic server error on 5xx and re-enables the cancel button', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('', { status: 503 }))
    useBatchStore.getState().addJob(makeJob({ job_id: 'r', status: 'running', progress: 0.5 }))
    render(<BatchJobList />)
    fireEvent.click(screen.getByTestId('batch-cancel-r'))
    await waitFor(() => {
      expect(screen.getByTestId('batch-error-r').textContent).toMatch(/503/)
    })
    const btn = screen.getByTestId('batch-cancel-r') as HTMLButtonElement
    expect(btn.disabled).toBe(false)
  })

  it('formats elapsed time relative to submitted_at using injected clock', () => {
    useBatchStore.getState().addJob(makeJob({ job_id: 'a', submitted_at: 1000 }))
    const fakeNow = () => 1000 + 75_000 // +1m15s
    render(<BatchJobList now={fakeNow} />)
    expect(screen.getByTestId('batch-elapsed-a').textContent).toBe('1:15')
  })

  it('shows the failure error string on failed jobs', () => {
    useBatchStore.getState().addJob(
      makeJob({ job_id: 'f', status: 'failed', progress: 0.3, error: 'render exploded' }),
    )
    render(<BatchJobList />)
    expect(screen.getByTestId('batch-job-error-f').textContent).toContain('render exploded')
  })
})
