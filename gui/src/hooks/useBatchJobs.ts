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
  /** Force a refresh: clear error state. */
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
  const [hasError, setHasError] = useState(false)
  const [isReconnecting, setIsReconnecting] = useState(false)
  // Refs that survive across renders without re-triggering the effect.
  const errorCountRef = useRef(0)
  const updateQueueRef = useRef<BatchProgressApiResponse['jobs']>([])
  const flushScheduledRef = useRef(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pollingRef = useRef(false)
  const cancelledRef = useRef(false)

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
    errorCountRef.current = 0
    setHasError(false)
    setIsReconnecting(false)

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
        if (cancelledRef.current) return
        errorCountRef.current = 0
        setHasError(false)
        setIsReconnecting(false)
      } catch {
        if (cancelledRef.current) return
        errorCountRef.current += 1
        setHasError(true)
        if (errorCountRef.current >= RECONNECTING_THRESHOLD) setIsReconnecting(true)
      } finally {
        pollingRef.current = false
      }
    }

    const schedule = (delay: number): void => {
      if (timerRef.current !== null) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => {
        if (cancelledRef.current) return
        if (allJobsTerminal(batchId)) return
        void pollOnce().then(() => {
          if (cancelledRef.current) return
          if (allJobsTerminal(batchId)) return
          schedule(computeBackoff(errorCountRef.current))
        })
      }, delay)
    }

    void pollOnce().then(() => {
      if (cancelledRef.current) return
      if (allJobsTerminal(batchId)) return
      schedule(computeBackoff(errorCountRef.current))
    })

    return () => {
      cancelledRef.current = true
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
    }
  }, [batchId, allJobsTerminal, queueUpdates])

  const refresh = useCallback(() => {
    errorCountRef.current = 0
    setHasError(false)
    setIsReconnecting(false)
  }, [])

  return {
    hasError,
    isReconnecting,
    refresh,
  }
}

// Test-only export for unit testing internal helpers.
export const __test = { coerceStatus, NORMAL_INTERVAL_MS, MAX_BACKOFF_MS, INITIAL_BACKOFF_MS }
