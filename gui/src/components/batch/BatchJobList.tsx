import { useState } from 'react'
import {
  TERMINAL_BATCH_STATUSES,
  useBatchStore,
  type BatchJob,
  type BatchJobStatus,
} from '../../stores/batchStore'

interface BatchJobListProps {
  /**
   * Optional batch_id filter — when provided, only jobs in that batch
   * are rendered. Unset means render all jobs in the store.
   */
  batchId?: string
  /** Override clock for deterministic elapsed-time tests. */
  now?: () => number
}

const STATUS_BADGE_CLASSES: Record<BatchJobStatus, string> = {
  queued: 'bg-gray-600 text-gray-100',
  running: 'bg-blue-600 text-white',
  completed: 'bg-green-600 text-white',
  failed: 'bg-red-600 text-white',
  cancelled: 'bg-gray-500 text-gray-100',
}

function formatElapsed(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

interface JobRowProps {
  job: BatchJob
  now: () => number
}

function JobRow({ job, now }: JobRowProps) {
  const removeJob = useBatchStore((s) => s.removeJob)
  const updateJob = useBatchStore((s) => s.updateJob)
  const [cancelling, setCancelling] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isTerminal = TERMINAL_BATCH_STATUSES.has(job.status)
  const progressPct = Math.round(Math.max(0, Math.min(1, job.progress)) * 100)
  const elapsed = formatElapsed(now() - job.submitted_at)

  const handleCancel = async (): Promise<void> => {
    if (cancelling || isTerminal) return
    setCancelling(true)
    setError(null)
    try {
      const res = await fetch(`/api/v1/render/batch/${job.job_id}`, { method: 'DELETE' })
      if (res.status === 404) {
        setError('Job not found')
        removeJob(job.job_id)
        return
      }
      if (res.status === 409) {
        setError('Job already finished')
        return
      }
      if (!res.ok) {
        setError(`Server error (${res.status})`)
        return
      }
      const data: unknown = await res.json().catch(() => null)
      const status = (data as { status?: string } | null)?.status
      if (status === 'cancelled') {
        updateJob({ job_id: job.job_id, status: 'cancelled' })
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Cancel failed')
    } finally {
      setCancelling(false)
    }
  }

  return (
    <div
      data-testid={`batch-job-row-${job.job_id}`}
      className="grid grid-cols-12 items-center gap-3 rounded border border-gray-700 bg-gray-900 px-3 py-2"
    >
      <div className="col-span-3 truncate text-xs text-gray-300" title={job.job_id}>
        {job.job_id}
      </div>
      <div className="col-span-2">
        <span
          data-testid={`batch-status-${job.job_id}`}
          className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${STATUS_BADGE_CLASSES[job.status]}`}
        >
          {job.status}
        </span>
      </div>
      <div className="col-span-4">
        <div className="h-2 w-full overflow-hidden rounded bg-gray-700">
          <div
            data-testid={`batch-progress-bar-${job.job_id}`}
            className="h-full bg-blue-500 transition-[width] duration-150"
            style={{ width: `${progressPct}%` }}
            role="progressbar"
            aria-valuenow={progressPct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Job ${job.job_id} progress`}
          />
        </div>
        <div className="mt-1 flex justify-between text-xs text-gray-400">
          <span data-testid={`batch-progress-pct-${job.job_id}`}>{progressPct}%</span>
          <span data-testid={`batch-elapsed-${job.job_id}`}>{elapsed}</span>
        </div>
      </div>
      <div className="col-span-3 flex justify-end">
        {!isTerminal && (
          <button
            type="button"
            data-testid={`batch-cancel-${job.job_id}`}
            onClick={handleCancel}
            disabled={cancelling}
            className="rounded bg-gray-700 px-2 py-1 text-xs text-gray-200 hover:bg-red-700 disabled:opacity-50"
          >
            {cancelling ? 'Cancelling…' : 'Cancel'}
          </button>
        )}
        {error && (
          <p
            data-testid={`batch-error-${job.job_id}`}
            className="ml-2 text-xs text-red-400"
            role="alert"
          >
            {error}
          </p>
        )}
        {job.error && job.status === 'failed' && (
          <p
            data-testid={`batch-job-error-${job.job_id}`}
            className="ml-2 truncate text-xs text-red-400"
            title={job.error}
          >
            {job.error}
          </p>
        )}
      </div>
    </div>
  )
}

/**
 * Live list of batch jobs (FR-002, FR-003). Each row shows a progress
 * bar, status badge, elapsed time, and a Cancel button (only for
 * non-terminal jobs).
 */
export default function BatchJobList({ batchId, now = Date.now }: BatchJobListProps) {
  const jobs = useBatchStore((s) =>
    batchId === undefined ? s.jobs : s.jobs.filter((j) => j.batch_id === batchId),
  )

  if (jobs.length === 0) {
    return (
      <p data-testid="batch-job-list-empty" className="text-sm text-gray-400">
        No batch jobs yet.
      </p>
    )
  }

  return (
    <div data-testid="batch-job-list" className="space-y-2">
      {jobs.map((job) => (
        <JobRow key={job.job_id} job={job} now={now} />
      ))}
    </div>
  )
}
