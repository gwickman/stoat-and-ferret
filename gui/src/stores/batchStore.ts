import { create } from 'zustand'

/** Batch job statuses returned by the backend. */
export type BatchJobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'

/** Statuses considered terminal — polling stops when all jobs are terminal. */
export const TERMINAL_BATCH_STATUSES: ReadonlySet<BatchJobStatus> = new Set([
  'completed',
  'failed',
  'cancelled',
])

/** A single batch job tracked client-side (mirrors BatchJobStatusResponse). */
export interface BatchJob {
  job_id: string
  batch_id: string
  project_id: string
  status: BatchJobStatus
  /** Render progress, 0.0-1.0 (NFR/INV-003). */
  progress: number
  error: string | null
  /** Wall-clock ms when the job entered the queue (used for elapsed display). */
  submitted_at: number
}

/** Patch shape used by `updateJob` — only mutable fields are accepted. */
export type BatchJobUpdate = Partial<Pick<BatchJob, 'status' | 'progress' | 'error'>> & {
  job_id: string
}

interface BatchStoreState {
  /** All known jobs (across all batches in this session). */
  jobs: BatchJob[]
  /** Whether a batch submission is currently in flight. */
  submitting: boolean
  /** Last submission error message, if any. */
  submitError: string | null

  addJob: (job: BatchJob) => void
  updateJob: (update: BatchJobUpdate) => void
  removeJob: (jobId: string) => void
  setSubmitting: (submitting: boolean) => void
  setSubmitError: (error: string | null) => void
  reset: () => void
}

const initialState = {
  jobs: [] as BatchJob[],
  submitting: false,
  submitError: null as string | null,
}

/**
 * Session-only Zustand store for batch render jobs.
 *
 * Per BL-295 NFR-002, this store does not persist to localStorage or
 * sessionStorage. Jobs only live in memory for the current page session.
 */
export const useBatchStore = create<BatchStoreState>((set) => ({
  ...initialState,

  addJob: (job) =>
    set((state) => {
      // Idempotent insert: if a job with the same id is already present,
      // merge the new fields onto the existing record instead of duplicating.
      const idx = state.jobs.findIndex((j) => j.job_id === job.job_id)
      if (idx >= 0) {
        const updated = [...state.jobs]
        updated[idx] = { ...updated[idx], ...job }
        return { jobs: updated }
      }
      return { jobs: [...state.jobs, job] }
    }),

  updateJob: (update) =>
    set((state) => {
      const idx = state.jobs.findIndex((j) => j.job_id === update.job_id)
      if (idx < 0) return state
      const existing = state.jobs[idx]
      const merged: BatchJob = {
        ...existing,
        status: update.status ?? existing.status,
        progress: update.progress ?? existing.progress,
        error: update.error !== undefined ? update.error : existing.error,
      }
      // INV-003: progress must not decrease unless the job is re-queued.
      if (
        update.progress !== undefined &&
        update.progress < existing.progress &&
        merged.status !== 'queued'
      ) {
        merged.progress = existing.progress
      }
      const next = [...state.jobs]
      next[idx] = merged
      return { jobs: next }
    }),

  removeJob: (jobId) =>
    set((state) => ({ jobs: state.jobs.filter((j) => j.job_id !== jobId) })),

  setSubmitting: (submitting) => set({ submitting }),

  setSubmitError: (submitError) => set({ submitError }),

  reset: () => set({ ...initialState }),
}))
