import { useCallback, useEffect, useRef, useState } from 'react'
import {
  TERMINAL_BATCH_STATUSES,
  useBatchStore,
  type BatchJob,
  type BatchJobStatus,
} from '../stores/batchStore'

/** Polling cadence (ms) when the server is responding normally. */
const NORMAL_INTERVAL_MS = 1000
/** Initial backoff after the first error. */
const INITIAL_BACKOFF_MS = 1000
/** Maximum backoff cap, per FR-002. */
const MAX_BACKOFF_MS = 10_000
/** Number of consecutive errors after which we surface a "reconnecting" hint. */
const RECONNECTING_THRESHOLD = 2

interface BatchProgressApiResponse {
  batch_id: string
  overall_progress: number
  completed_jobs: number
  failed_jobs: number
  total_jobs: number
  jobs: Array<{
    job_id: string
    project_id: string
    status: string
    progress: number
    error: string | null
  }>
}

/** Coerce a raw status string from the API into our union type. */
function coerceStatus(raw: string): BatchJobStatus {
  if (
    raw === 'queued' ||
    raw === 'running' ||
    raw === 'completed' ||
    raw === 'failed' ||
    raw === 'cancelled'
  ) {
    return raw
  }
  return 'queued'
}

/** Public state surface of the hook. */
export interface UseBatchJobsResult {
  /** True if the most recent poll request failed (>=1 consecutive errors). */
  hasError: boolean
  /** True after RECONNECTING_THRESHOLD consecutive errors. */
  isReconnecting: boolean
  /** Force an immediate refresh (bypasses the current backoff timer). */
  refresh: () => void
}

/**
 * Poll batch progress for a given batch_id and feed updates into the
 * batchStore. Implements:
 *
 *   - 1 s normal cadence (FR-002)
 *   - Exponential backoff on error: 1s -> 2s -> 4s capped at 10s (FR-002)
 *   - Polling stops automatically when all jobs are terminal (FR-002)
 *   - Ref-queue pattern (LRN-188 / NFR-001) — rapid responses are queued
 *     into a `useRef` and flushed via `queueMicrotask`, preventing React's
 *     state batching from collapsing concurrent updates.
 *
 * Pass `null` to disable polling (e.g. when no batch has been submitted yet).
 */
export function useBatchJobs(batchId: string | null): UseBatchJobsResult {
  const [errorCount, setErrorCount] = useState(0)
  // Update queue holds raw API job rows that have not yet been merged into
  // the store. Flushed in a microtask so a burst of polls collapses to a
  // single coherent batch of `updateJob` calls.
  const updateQueueRef = useRef<BatchProgressApiResponse['jobs']>([])
  const flushScheduledRef = useRef(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pollingRef = useRef(false)
  const cancelledRef = useRef(false)
  // Tracks the last computed delay so `refresh` can skip the pending wait.
  const refreshNonceRef = useRef(0)

  const flushQueue = useCallback(() => {
    flushScheduledRef.current = false
    if (updateQueueRef.current.length === 0) return
    const batch = updateQueueRef.current
    updateQueueRef.current = []
    const store = useBatchStore.getState()
    for (const row of batch) {
      store.updateJob({
        job_id: row.job_id,
        status: coerceStatus(row.status),
        progress: row.progress,
        error: row.error,
      })
    }
  }, [])

  const queueUpdates = useCallback(
    (jobs: BatchProgressApiResponse['jobs']) => {
      if (jobs.length === 0) return
      updateQueueRef.current.push(...jobs)
      if (!flushScheduledRef.current) {
        flushScheduledRef.current = true
        queueMicrotask(flushQueue)
      }
    },
    [flushQueue],
  )

  const allJobsTerminal = useCallback((batchIdLocal: string): boolean => {
    const jobs = useBatchStore
      .getState()
      .jobs.filter((j: BatchJob) => j.batch_id === batchIdLocal)
    if (jobs.length === 0) return false
    return jobs.every((j) => TERMINAL_BATCH_STATUSES.has(j.status))
  }, [])

  useEffect(() => {
    if (batchId === null) return undefined
    cancelledRef.current = false

    const computeBackoff = (errors: number): number => {
      if (errors === 0) return NORMAL_INTERVAL_MS
      const delay = INITIAL_BACKOFF_MS * 2 ** (errors - 1)
      return Math.min(delay, MAX_BACKOFF_MS)
    }

    const pollOnce = async (): Promise<void> => {
      if (cancelledRef.current) return
      if (pollingRef.current) return
      pollingRef.current = true
      try {
        const res = await fetch(`/api/v1/render/batch/${batchId}`)
        if (!res.ok) {
          throw new Error(`status ${res.status}`)
        }
        const json = (await res.json()) as BatchProgressApiResponse
        queueUpdates(json.jobs)
        if (!cancelledRef.current) setErrorCount(0)
      } catch {
        if (!cancelledRef.current) setErrorCount((n) => n + 1)
      } finally {
        pollingRef.current = false
      }
    }

    const schedule = (delay: number, nonce: number): void => {
      if (timerRef.current !== null) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => {
        if (cancelledRef.current) return
        if (nonce !== refreshNonceRef.current) return
        if (allJobsTerminal(batchId)) return
        void pollOnce().then(() => {
          if (cancelledRef.current) return
          if (allJobsTerminal(batchId)) return
          schedule(computeBackoff(errorCount), refreshNonceRef.current)
        })
      }, delay)
    }

    // Kick off an immediate poll, then settle into the cadence.
    void pollOnce().then(() => {
      if (cancelledRef.current) return
      if (allJobsTerminal(batchId)) return
      schedule(computeBackoff(errorCount), refreshNonceRef.current)
    })

    return () => {
      cancelledRef.current = true
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
    }
    // We deliberately re-establish the polling chain when errorCount
    // changes so the next scheduled tick uses the updated backoff.
  }, [batchId, errorCount, allJobsTerminal, queueUpdates])

  const refresh = useCallback(() => {
    refreshNonceRef.current += 1
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
    if (batchId === null) return
    setErrorCount(0)
  }, [batchId])

  return {
    hasError: errorCount > 0,
    isReconnecting: errorCount >= RECONNECTING_THRESHOLD,
    refresh,
  }
}

// Test-only export for unit testing internal helpers.
export const __test = { coerceStatus, NORMAL_INTERVAL_MS, MAX_BACKOFF_MS, INITIAL_BACKOFF_MS }
