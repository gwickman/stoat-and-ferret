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
    expect(fetchSpy.mock.calls).toHaveLength(callsAfterImmediate)
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
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network down'))
    renderHook(() => useBatchJobs('b1'))
    await settle()
    const callsAfterMount = fetchSpy.mock.calls.length
    for (let i = 0; i < 6; i++) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(__test.MAX_BACKOFF_MS + 100)
      })
      await settle()
    }
    expect(fetchSpy.mock.calls.length).toBeGreaterThan(callsAfterMount + 4)
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
    expect(fetchSpy.mock.calls).toHaveLength(before)
  })

  it('does not schedule further polling when in-flight poll resolves after unmount', async () => {
    let resolveFetch!: (r: Response) => void
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockReturnValueOnce(
      new Promise<Response>((resolve) => { resolveFetch = resolve }),
    )

    const { unmount } = renderHook(() => useBatchJobs('b1'))
    // Hook started; initial poll is in-flight (fetch not yet resolved)

    // Unmount before fetch resolves — sets cancelledRef.current = true via cleanup
    unmount()

    // Resolve the in-flight fetch after unmount
    resolveFetch(
      makeResponse([
        { job_id: 'j1', project_id: 'p1', status: 'running', progress: 0.5, error: null },
      ]),
    )

    await settle()

    // Store-invariant assertion (BL-767-AC-2): the post-unmount update must NOT reach the store.
    // Before the fix, queueUpdates ran before the guard, so flushQueue mutated the store.
    // After the fix, the guard fires before queueUpdates, keeping j1 at its pre-unmount value.
    expect(
      useBatchStore.getState().jobs.find((j) => j.job_id === 'j1')?.status,
    ).toBe('queued')

    // cancelledRef.current is true; no timer should be scheduled
    expect(vi.getTimerCount()).toBe(0)
    // Advance past NORMAL_INTERVAL_MS and verify no additional fetches occurred
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3 * __test.NORMAL_INTERVAL_MS)
    })
    await settle()
    expect(fetchSpy.mock.calls).toHaveLength(1)
  })

  it('ignores stale b1 fetch resolving after batchId changes to b2', async () => {
    let resolveB1Fetch!: (r: Response) => void
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(
        new Promise<Response>((resolve) => {
          resolveB1Fetch = resolve
        }),
      )
      .mockResolvedValue(
        new Response(
          JSON.stringify({
            batch_id: 'b2',
            overall_progress: 0,
            completed_jobs: 0,
            failed_jobs: 0,
            total_jobs: 0,
            jobs: [],
          }),
          { status: 200 },
        ),
      )

    // b2 already has a known job in the store so a later store update is observable
    // (updateJob only merges onto an existing job_id; it does not insert new rows).
    useBatchStore.getState().addJob({
      job_id: 'j-b2',
      batch_id: 'b2',
      project_id: 'p3',
      status: 'queued',
      progress: 0,
      error: null,
      submitted_at: 0,
    })

    const { rerender } = renderHook(
      ({ batchId }: { batchId: string | null }) => useBatchJobs(batchId),
      { initialProps: { batchId: 'b1' as string | null } },
    )
    // b1 initial poll is in-flight (fetch not yet resolved)

    // Switch to b2: triggers b1 cleanup (cancelledRef.current=true) then b2 effect
    // (cancelledRef.current=false). b1's stale response must not mutate the store.
    await act(async () => {
      rerender({ batchId: 'b2' })
    })

    // Resolve b1's stale fetch — guard (now before queueUpdates) must catch this
    resolveB1Fetch(
      makeResponse([
        { job_id: 'j1', project_id: 'p1', status: 'running', progress: 0.5, error: null },
      ]),
    )
    await settle()

    // j1 was 'queued' before the batchId switch; b1's stale 'running' update must not reach the store
    expect(
      useBatchStore.getState().jobs.find((j) => j.job_id === 'j1')?.status,
    ).toBe('queued')

    // Also verify b2 polling independently reflects in the store (LRN-978:
    // characterization-scope gap) — proves b2 is live, not only that b1's stale
    // response was blocked. Mounted as a fresh hook instance (own refs) rather
    // than driven through the first instance's pending schedule() timer, since the
    // first instance's stale-but-unresolved b1 poll still holds pollingRef.current
    // exclusively (only one fetch in flight per hook instance by design) — a second
    // instance is the direct way to observe an unblocked b2 poll reaching the store.
    fetchSpy.mockResolvedValueOnce(
      makeResponse([
        { job_id: 'j-b2', project_id: 'p3', status: 'running', progress: 0.4, error: null },
      ]),
    )
    renderHook(() => useBatchJobs('b2'))
    await settle()
    expect(
      useBatchStore.getState().jobs.find((j) => j.job_id === 'j-b2')?.status,
    ).toBe('running')
  })

  it('stale b1 rejection after batchId change does not pollute b2 error state', async () => {
    let rejectB1Fetch!: (err: Error) => void
    vi.spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(
        new Promise<Response>((_, reject) => {
          rejectB1Fetch = reject
        }),
      )
      .mockResolvedValue(
        new Response(
          JSON.stringify({
            batch_id: 'b2',
            overall_progress: 0,
            completed_jobs: 0,
            failed_jobs: 0,
            total_jobs: 0,
            jobs: [],
          }),
          { status: 200 },
        ),
      )

    const { result, rerender } = renderHook(
      ({ batchId }: { batchId: string | null }) => useBatchJobs(batchId),
      { initialProps: { batchId: 'b1' as string | null } },
    )
    // b1 initial poll is in-flight (fetch not yet resolved/rejected)

    // Switch to b2: triggers b1 cleanup (cancelledRef.current=true) then b2 effect
    // (cancelledRef.current=false, activeBatchIdRef.current='b2')
    await act(async () => {
      rerender({ batchId: 'b2' })
    })

    // Reject the stale b1 fetch — the catch-block guard (BL-769) must catch this
    rejectB1Fetch(new Error('network error'))
    await settle()

    // b2 error state must remain clean — the stale b1 rejection must not set it
    expect(result.current.hasError).toBe(false)
    expect(result.current.isReconnecting).toBe(false)
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
