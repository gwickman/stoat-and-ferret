/**
 * Displays a single render job card with progress bar, ETA, speed ratio,
 * status badge, and action buttons (cancel, retry, delete).
 */

import { useState } from 'react'
import StatusBadge from './StatusBadge'
import { useRenderStore, type RenderJob } from '../../stores/renderStore'

function formatEta(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}m ${s}s`
}

interface RenderJobCardProps {
  job: RenderJob
}

export default function RenderJobCard({ job }: RenderJobCardProps) {
  const fetchJobs = useRenderStore((s) => s.fetchJobs)
  const [retryError, setRetryError] = useState<string | null>(null)
  const [retryDisabled, setRetryDisabled] = useState(false)
  const [cancelLoading, setCancelLoading] = useState(false)
  const [retryLoading, setRetryLoading] = useState(false)
  const [deleteLoading, setDeleteLoading] = useState(false)

  const canCancel = job.status === 'queued' || job.status === 'running'
  const canRetry = job.status === 'failed' && !retryDisabled

  async function handleCancel() {
    setCancelLoading(true)
    try {
      const res = await fetch(`/api/v1/render/${job.id}/cancel`, { method: 'POST' })
      if (res.ok) await fetchJobs()
    } finally {
      setCancelLoading(false)
    }
  }

  async function handleRetry() {
    setRetryLoading(true)
    try {
      const res = await fetch(`/api/v1/render/${job.id}/retry`, { method: 'POST' })
      if (res.status === 409) {
        const body = await res.json().catch(() => null)
        setRetryError(body?.detail?.message || body?.detail || 'Retry limit reached')
        setRetryDisabled(true)
        return
      }
      if (res.ok) await fetchJobs()
    } finally {
      setRetryLoading(false)
    }
  }

  async function handleDelete() {
    if (!window.confirm('Delete this render job?')) return
    setDeleteLoading(true)
    try {
      const res = await fetch(`/api/v1/render/${job.id}`, { method: 'DELETE' })
      if (res.ok) await fetchJobs()
    } finally {
      setDeleteLoading(false)
    }
  }

  return (
    <div
      className="rounded-lg border border-gray-700 bg-gray-800 p-4"
      data-testid={`render-job-card-${job.id}`}
    >
      {/* Header: job ID + status badge */}
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm font-medium">{job.id}</span>
        <StatusBadge status={job.status} />
      </div>

      {/* Progress bar */}
      <div className="mb-2 h-2 rounded bg-gray-700" data-testid="progress-bar-track">
        <div
          className="h-full rounded bg-blue-500 transition-[width] duration-200"
          data-testid="progress-bar-fill"
          style={{ width: `${Math.min(100, job.progress * 100)}%` }}
        />
      </div>

      {/* ETA and speed info */}
      <div className="mb-3 flex items-center gap-4 text-xs text-gray-400">
        <span>{Math.round(job.progress * 100)}%</span>
        {job.eta_seconds != null && (
          <span data-testid="eta-text">ETA {formatEta(job.eta_seconds)}</span>
        )}
        {job.speed_ratio != null && (
          <span data-testid="speed-text">{job.speed_ratio.toFixed(1)}x real-time</span>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={!canCancel || cancelLoading}
          onClick={handleCancel}
          data-testid="cancel-btn"
          className="rounded bg-gray-700 px-3 py-1 text-xs text-gray-200 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="button"
          disabled={!canRetry || retryLoading}
          onClick={handleRetry}
          data-testid="retry-btn"
          className="rounded bg-gray-700 px-3 py-1 text-xs text-gray-200 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Retry
        </button>
        <button
          type="button"
          disabled={deleteLoading}
          onClick={handleDelete}
          data-testid="delete-btn"
          className="rounded bg-gray-700 px-3 py-1 text-xs text-red-400 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Delete
        </button>
      </div>

      {/* Retry error message */}
      {retryError && (
        <p className="mt-2 text-xs text-red-400" data-testid="retry-error">
          {retryError}
        </p>
      )}
    </div>
  )
}
