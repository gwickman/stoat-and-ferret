import { useEffect, useMemo, useRef, useState } from 'react'
import { useRenderStore, type RenderJob } from '../stores/renderStore'
import { useBatchJobs } from '../hooks/useBatchJobs'
import { useAnnounce } from '../hooks/useAnnounce'
import RenderJobCard from '../components/render/RenderJobCard'
import StartRenderModal from '../components/render/StartRenderModal'
import BatchPanel from '../components/batch/BatchPanel'
import BatchJobList from '../components/batch/BatchJobList'

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

type RenderTab = 'queue' | 'batch'

interface FlagsResponse {
  testing_mode: boolean
  seed_endpoint: boolean
  synthetic_monitoring: boolean
  batch_rendering: boolean
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
  const [startModalOpen, setStartModalOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<RenderTab>('queue')
  // Track the most recently submitted batch so the polling hook can
  // follow it.
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null)
  // Whether the batch_rendering feature flag is enabled. Defaults to
  // false so the tab stays hidden until the API confirms it.
  const [batchEnabled, setBatchEnabled] = useState<boolean>(false)

  const { announce } = useAnnounce()

  // Track previous job states to detect status/progress transitions.
  const prevJobsRef = useRef(new Map<string, RenderJob>())
  // Debounce ref for progress announcements (one active timeout across all jobs).
  const progressDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    fetchJobs()
    fetchQueueStatus()
    fetchEncoders()
    fetchFormats()
  }, [fetchJobs, fetchQueueStatus, fetchEncoders, fetchFormats])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const res = await fetch('/api/v1/flags')
        if (!res.ok) throw new Error(`flags ${res.status}`)
        const data = (await res.json()) as Partial<FlagsResponse>
        if (cancelled) return
        setBatchEnabled(data.batch_rendering === true)
      } catch {
        if (cancelled) return
        // Failure mode: treat flag as false (per requirements failure modes).
        setBatchEnabled(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  // If the flag flips off after we've selected the batch tab, fall back.
  useEffect(() => {
    if (!batchEnabled && activeTab === 'batch') setActiveTab('queue')
  }, [batchEnabled, activeTab])

  // Announce job status transitions (progress, completion, failure).
  useEffect(() => {
    const prevMap = prevJobsRef.current
    const newMap = new Map(jobs.map((j) => [j.id, j]))
    prevJobsRef.current = newMap

    for (const [, job] of newMap) {
      const prev = prevMap.get(job.id)
      if (!prev) continue

      // Progress changed for a running job — debounce to 2s.
      if (job.status === 'running' && prev.progress !== job.progress) {
        const clamped = Math.min(100, Math.max(0, Math.round(job.progress * 100)))
        if (progressDebounceRef.current) clearTimeout(progressDebounceRef.current)
        progressDebounceRef.current = setTimeout(() => {
          announce(`Rendering: ${clamped}% complete`)
        }, 2000)
      }

      // Job completed — cancel pending progress debounce and announce immediately.
      if (prev.status !== 'completed' && job.status === 'completed') {
        if (progressDebounceRef.current) {
          clearTimeout(progressDebounceRef.current)
          progressDebounceRef.current = null
        }
        announce('Render complete')
      }

      // Job failed — announce immediately with assertive priority.
      if (prev.status !== 'failed' && job.status === 'failed') {
        const msg = job.error_message ?? 'operation failed'
        announce(`Error: ${msg}`, 'assertive')
      }
    }
  }, [jobs, announce])

  // Announce store-level fetch errors (e.g. network failures).
  const prevErrorRef = useRef<string | null>(null)
  useEffect(() => {
    if (error && error !== prevErrorRef.current) {
      announce(`Error: ${error}`, 'assertive')
    }
    prevErrorRef.current = error
  }, [error, announce])

  // Clean up progress debounce timer on unmount.
  useEffect(() => {
    return () => {
      if (progressDebounceRef.current) clearTimeout(progressDebounceRef.current)
    }
  }, [])

  useBatchJobs(activeTab === 'batch' ? activeBatchId : null)

  const { active, pending, completed } = useMemo(() => categorizeJobs(jobs), [jobs])

  return (
    <div className="p-6" role="main" id="main-content" tabIndex={-1} data-testid="render-page">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Render</h2>
        {activeTab === 'queue' && (
          <button
            type="button"
            onClick={() => setStartModalOpen(true)}
            data-testid="start-render-btn"
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Start Render
          </button>
        )}
      </div>

      {/* Tab strip */}
      <div data-testid="render-tabs" className="mb-4 flex gap-2 border-b border-gray-700">
        <button
          type="button"
          data-testid="render-tab-queue"
          onClick={() => setActiveTab('queue')}
          className={`px-4 py-2 text-sm font-medium ${
            activeTab === 'queue'
              ? 'border-b-2 border-blue-500 text-blue-400'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          Render Queue
        </button>
        {batchEnabled && (
          <button
            type="button"
            data-testid="render-tab-batch"
            onClick={() => setActiveTab('batch')}
            className={`px-4 py-2 text-sm font-medium ${
              activeTab === 'batch'
                ? 'border-b-2 border-blue-500 text-blue-400'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            Batch
          </button>
        )}
      </div>

      {activeTab === 'queue' && (
        <div data-testid="render-tab-queue-content">
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
                <p className="text-sm text-gray-400">No active jobs</p>
              ) : (
                <div className="space-y-2">
                  {active.map((job) => (
                    <RenderJobCard key={job.id} job={job} />
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Pending Jobs */}
          <div data-testid="pending-jobs-section" className="mb-6">
            <h3 className="mb-2 text-lg font-medium">Pending</h3>
            <div data-testid="job-list">
              {pending.length === 0 ? (
                <p className="text-sm text-gray-400">No pending jobs</p>
              ) : (
                <div className="space-y-2">
                  {pending.map((job) => (
                    <RenderJobCard key={job.id} job={job} />
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Completed Jobs */}
          <div data-testid="completed-jobs-section" className="mb-6">
            <h3 className="mb-2 text-lg font-medium">Completed</h3>
            <div data-testid="job-list">
              {completed.length === 0 ? (
                <p className="text-sm text-gray-400">No completed jobs</p>
              ) : (
                <div className="space-y-2">
                  {completed.map((job) => (
                    <RenderJobCard key={job.id} job={job} />
                  ))}
                </div>
              )}
            </div>
          </div>

          <StartRenderModal
            open={startModalOpen}
            onClose={() => setStartModalOpen(false)}
            onSubmitted={() => fetchJobs()}
          />
        </div>
      )}

      {activeTab === 'batch' && batchEnabled && (
        <div data-testid="render-tab-batch-content" className="space-y-4">
          <BatchPanel onBatchSubmitted={(id) => setActiveBatchId(id)} />
          <section
            data-testid="batch-job-list-section"
            aria-label="Batch jobs"
            className="rounded border border-gray-700 bg-gray-800 p-4"
          >
            <h3 className="mb-3 text-lg font-medium text-gray-200">Batch Jobs</h3>
            <BatchJobList batchId={activeBatchId ?? undefined} />
          </section>
        </div>
      )}
    </div>
  )
}
