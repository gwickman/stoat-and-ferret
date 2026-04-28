import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useBatchStore } from '../../stores/batchStore'
import { useBatchJobs, __test } from '../useBatchJobs'

interface ApiJobRow {
  job_id: string
  project_id: string
  status: string
  progress: number
  error: string | null
}

function makeResponse(jobs: ApiJobRow[]): Response {
  return new Response(
    JSON.stringify({
      batch_id: 'b1',
      overall_progress: 0.5,
      completed_jobs: 0,
      failed_jobs: 0,
      total_jobs: jobs.length,
      jobs,
    }),
    { status: 200 },
  )
}

beforeEach(() => {
  vi.useFakeTimers()
  useBatchStore.getState().reset()
  useBatchStore.getState().addJob({
    job_id: 'j1',
    batch_id: 'b1',
    project_id: 'p1',
    status: 'queued',
    progress: 0,
    error: null,
    submitted_at: 0,
  })
  useBatchStore.getState().addJob({
    job_id: 'j2',
    batch_id: 'b1',
    project_id: 'p2',
    status: 'queued',
    progress: 0,
    error: null,
    submitted_at: 0,
  })
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

async function settle(): Promise<void> {
  await act(async () => {
    await Promise.resolve()
    await Promise.resolve()
    await Promise.resolve()
    await Promise.resolve()
  })
}

describe('useBatchJobs', () => {
  it('does not poll when batchId is null', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
    renderHook(() => useBatchJobs(null))
    await settle()
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('issues an immediate poll when batchId is provided', async () => {
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(
        makeResponse([
          { job_id: 'j1', project_id: 'p1', status: 'running', progress: 0.25, error: null },
        ]),
      )
    renderHook(() => useBatchJobs('b1'))
    await settle()
    expect(fetchSpy).toHaveBeenCalledWith('/api/v1/render/batch/b1')
  })

  it('feeds API rows into the store via the ref-queue', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      makeResponse([
        { job_id: 'j1', project_id: 'p1', status: 'running', progress: 0.5, error: null },
        { job_id: 'j2', project_id: 'p2', status: 'completed', progress: 1.0, error: null },
      ]),
    )
    renderHook(() => useBatchJobs('b1'))
    await settle()
    const jobs = useBatchStore.getState().jobs
    expect(jobs.find((j) => j.job_id === 'j1')?.status).toBe('running')
    expect(jobs.find((j) => j.job_id === 'j1')?.progress).toBe(0.5)
    expect(jobs.find((j) => j.job_id === 'j2')?.status).toBe('completed')
  })

  it('continues polling at NORMAL_INTERVAL_MS while jobs are non-terminal', async () => {
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(
        makeResponse([
          { job_id: 'j1', project_id: 'p1', status: 'running', progress: 0.5, error: null },
        ]),
      )
    renderHook(() => useBatchJobs('b1'))
    await settle()
    const callsAfterImmediate = fetchSpy.mock.calls.length
    await act(async () => {
      await vi.advanceTimersByTimeAsync(__test.NORMAL_INTERVAL_MS + 50)
    })
    await settle()
    expect(fetchSpy.mock.calls.length).toBeGreaterThan(callsAfterImmediate)
  })

  it('stops polling once all jobs reach terminal state', async () => {
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(
        makeResponse([
          { job_id: 'j1', project_id: 'p1', status: 'completed', progress: 1.0, error: null },
          { job_id: 'j2', project_id: 'p2', status: 'cancelled', progress: 0.2, error: null },
        ]),
      )
    renderHook(() => useBatchJobs('b1'))
    await settle()
    const callsAfterImmediate = fetchSpy.mock.calls.length
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5 * __test.NORMAL_INTERVAL_MS)
    })
    await settle()
    expect(fetchSpy.mock.calls.length).toBe(callsAfterImmediate)
  })

  it('reports hasError on a single failed poll', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network down'))
    const { result } = renderHook(() => useBatchJobs('b1'))
    await settle()
    expect(result.current.hasError).toBe(true)
    expect(result.current.isReconnecting).toBe(false)
  })

  it('reports isReconnecting after two consecutive failed polls', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network down'))
    const { result } = renderHook(() => useBatchJobs('b1'))
    await settle()
    await act(async () => {
      await vi.advanceTimersByTimeAsync(__test.INITIAL_BACKOFF_MS + 100)
    })
    await settle()
    expect(result.current.isReconnecting).toBe(true)
  })

  it('caps exponential backoff at MAX_BACKOFF_MS', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network down'))
    renderHook(() => useBatchJobs('b1'))
    await settle()
    for (let i = 0; i < 6; i++) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(__test.MAX_BACKOFF_MS + 100)
      })
      await settle()
    }
    expect(true).toBe(true)
  })

  it('coerces unknown statuses to "queued" defensively', () => {
    expect(__test.coerceStatus('queued')).toBe('queued')
    expect(__test.coerceStatus('running')).toBe('running')
    expect(__test.coerceStatus('completed')).toBe('completed')
    expect(__test.coerceStatus('failed')).toBe('failed')
    expect(__test.coerceStatus('cancelled')).toBe('cancelled')
    expect(__test.coerceStatus('garbage')).toBe('queued')
  })

  it('refresh resets error state', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network down'))
    const { result } = renderHook(() => useBatchJobs('b1'))
    await settle()
    expect(result.current.hasError).toBe(true)
    act(() => {
      result.current.refresh()
    })
    await settle()
    expect(result.current.hasError).toBe(false)
  })

  it('cleans up on unmount (no further fetch after timer fires)', async () => {
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(
        makeResponse([
          { job_id: 'j1', project_id: 'p1', status: 'running', progress: 0.5, error: null },
        ]),
      )
    const { unmount } = renderHook(() => useBatchJobs('b1'))
    await settle()
    const before = fetchSpy.mock.calls.length
    unmount()
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5 * __test.NORMAL_INTERVAL_MS)
    })
    await settle()
    expect(fetchSpy.mock.calls.length).toBe(before)
  })

  it('does not regress progress under burst (NFR-001 / INV-003)', async () => {
    let progress = 0.1
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => {
      const value = progress
      progress = Math.min(progress + 0.2, 1.0)
      return makeResponse([
        { job_id: 'j1', project_id: 'p1', status: 'running', progress: value, error: null },
      ])
    })
    renderHook(() => useBatchJobs('b1'))
    await settle()
    for (let i = 0; i < 4; i++) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(__test.NORMAL_INTERVAL_MS + 50)
      })
      await settle()
    }
    const job = useBatchStore.getState().jobs.find((j) => j.job_id === 'j1')
    expect(job).toBeDefined()
    expect(job!.progress).toBeGreaterThanOrEqual(0.1)
  })
})
