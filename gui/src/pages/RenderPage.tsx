import { useEffect, useMemo } from 'react'
import { useRenderStore, type RenderJob } from '../stores/renderStore'
import { useRenderEvents } from '../hooks/useRenderEvents'

/** Categorize jobs into active, pending, and completed buckets. */
function categorizeJobs(jobs: RenderJob[]) {
  const active: RenderJob[] = []
  const pending: RenderJob[] = []
  const completed: RenderJob[] = []

  for (const job of jobs) {
    switch (job.status) {
      case 'running':
        active.push(job)
        break
      case 'queued':
        pending.push(job)
        break
      case 'completed':
      case 'failed':
      case 'cancelled':
        completed.push(job)
        break
      default:
        completed.push(job)
    }
  }

  return { active, pending, completed }
}

export default function RenderPage() {
  const jobs = useRenderStore((s) => s.jobs)
  const queueStatus = useRenderStore((s) => s.queueStatus)
  const isLoading = useRenderStore((s) => s.isLoading)
  const error = useRenderStore((s) => s.error)
  const fetchJobs = useRenderStore((s) => s.fetchJobs)
  const fetchQueueStatus = useRenderStore((s) => s.fetchQueueStatus)
  const fetchEncoders = useRenderStore((s) => s.fetchEncoders)
  const fetchFormats = useRenderStore((s) => s.fetchFormats)

  useRenderEvents()

  useEffect(() => {
    fetchJobs()
    fetchQueueStatus()
    fetchEncoders()
    fetchFormats()
  }, [fetchJobs, fetchQueueStatus, fetchEncoders, fetchFormats])

  const { active, pending, completed } = useMemo(() => categorizeJobs(jobs), [jobs])

  return (
    <div className="p-6" data-testid="render-page">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Render</h2>
        <button
          type="button"
          disabled={true}
          title="Available in a future update"
          data-testid="start-render-btn"
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          Start Render
        </button>
      </div>

      {/* Queue Status Bar */}
      <div
        data-testid="queue-status-bar"
        className="mb-6 flex items-center gap-6 rounded border border-gray-700 bg-gray-800 px-4 py-3 text-sm"
      >
        {queueStatus === null ? (
          <span className="text-gray-400">{isLoading ? 'Loading queue status…' : 'Queue status unavailable'}</span>
        ) : (
          <>
            <span>
              Active: <strong>{queueStatus.active_count}</strong>
            </span>
            <span>
              Pending: <strong>{queueStatus.pending_count}</strong>
            </span>
            <span>
              Capacity: <strong>{queueStatus.max_concurrent}</strong>
            </span>
          </>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded border border-red-800 bg-red-900/30 p-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {jobs.length === 0 && !isLoading && (
        <p className="text-gray-400" data-testid="empty-state">
          No render jobs
        </p>
      )}

      {/* Active Jobs */}
      <div data-testid="active-jobs-section" className="mb-6">
        <h3 className="mb-2 text-lg font-medium">Active</h3>
        <div data-testid="job-list">
          {active.length === 0 ? (
            <p className="text-sm text-gray-500">No active jobs</p>
          ) : (
            <ul className="space-y-2">
              {active.map((job) => (
                <li key={job.id} className="rounded border border-gray-700 bg-gray-800 p-3 text-sm">
                  <span className="font-medium">{job.id}</span> — {job.status}
                  {job.progress > 0 && <span className="ml-2 text-gray-400">({Math.round(job.progress * 100)}%)</span>}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Pending Jobs */}
      <div data-testid="pending-jobs-section" className="mb-6">
        <h3 className="mb-2 text-lg font-medium">Pending</h3>
        <div data-testid="job-list">
          {pending.length === 0 ? (
            <p className="text-sm text-gray-500">No pending jobs</p>
          ) : (
            <ul className="space-y-2">
              {pending.map((job) => (
                <li key={job.id} className="rounded border border-gray-700 bg-gray-800 p-3 text-sm">
                  <span className="font-medium">{job.id}</span> — {job.status}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Completed Jobs */}
      <div data-testid="completed-jobs-section" className="mb-6">
        <h3 className="mb-2 text-lg font-medium">Completed</h3>
        <div data-testid="job-list">
          {completed.length === 0 ? (
            <p className="text-sm text-gray-500">No completed jobs</p>
          ) : (
            <ul className="space-y-2">
              {completed.map((job) => (
                <li key={job.id} className="rounded border border-gray-700 bg-gray-800 p-3 text-sm">
                  <span className="font-medium">{job.id}</span> — {job.status}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
