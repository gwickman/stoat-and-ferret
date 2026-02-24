import { useCallback, useEffect, useRef, useState } from 'react'
import DirectoryBrowser from './DirectoryBrowser'

interface ScanModalProps {
  open: boolean
  onClose: () => void
  onScanComplete: () => void
}

type ScanStatus = 'idle' | 'scanning' | 'cancelling' | 'cancelled' | 'complete' | 'error'

interface JobStatus {
  job_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number | null
  result: Record<string, unknown> | null
  error: string | null
}

export default function ScanModal({
  open,
  onClose,
  onScanComplete,
}: ScanModalProps) {
  const [directory, setDirectory] = useState('')
  const [recursive, setRecursive] = useState(true)
  const [scanStatus, setScanStatus] = useState<ScanStatus>('idle')
  const [errorMessage, setErrorMessage] = useState('')
  const [progress, setProgress] = useState<number | null>(null)
  const [showBrowser, setShowBrowser] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const jobIdRef = useRef<string | null>(null)

  const cleanup = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!open) {
      cleanup()
      setScanStatus('idle')
      setDirectory('')
      setErrorMessage('')
      setProgress(null)
      setShowBrowser(false)
      jobIdRef.current = null
    }
  }, [open, cleanup])

  useEffect(() => () => cleanup(), [cleanup])

  async function handleCancel() {
    const jobId = jobIdRef.current
    if (!jobId || scanStatus !== 'scanning') return

    setScanStatus('cancelling')
    try {
      await fetch(`/api/v1/jobs/${jobId}/cancel`, { method: 'POST' })
    } catch {
      // Cancel request failed, polling will still detect final state
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!directory.trim()) return

    setScanStatus('scanning')
    setErrorMessage('')
    setProgress(null)

    try {
      const res = await fetch('/api/v1/videos/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: directory.trim(), recursive }),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ message: `Scan failed: ${res.status}` }))
        throw new Error(err.message || `Scan failed: ${res.status}`)
      }

      const { job_id }: { job_id: string } = await res.json()
      jobIdRef.current = job_id

      pollRef.current = setInterval(async () => {
        try {
          const statusRes = await fetch(`/api/v1/jobs/${job_id}`)
          if (!statusRes.ok) return
          const status: JobStatus = await statusRes.json()

          setProgress(status.progress)

          if (status.status === 'completed') {
            cleanup()
            setScanStatus('complete')
            onScanComplete()
          } else if (status.status === 'cancelled') {
            cleanup()
            setScanStatus('cancelled')
          } else if (status.status === 'failed') {
            cleanup()
            setScanStatus('error')
            setErrorMessage(status.error ?? 'Scan failed')
          }
        } catch {
          // polling error, keep trying
        }
      }, 1000)
    } catch (err) {
      setScanStatus('error')
      setErrorMessage(err instanceof Error ? err.message : 'Scan failed')
    }
  }

  if (!open) return null

  const isScanning = scanStatus === 'scanning' || scanStatus === 'cancelling'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      data-testid="scan-modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isScanning) onClose()
      }}
    >
      <div className="w-full max-w-md rounded-lg border border-gray-700 bg-gray-900 p-6">
        <h3 className="mb-4 text-lg font-semibold text-gray-100">
          Scan Directory
        </h3>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label
              htmlFor="scan-directory"
              className="mb-1 block text-sm text-gray-400"
            >
              Directory Path
            </label>
            <div className="flex gap-2">
              <input
                id="scan-directory"
                type="text"
                value={directory}
                onChange={(e) => setDirectory(e.target.value)}
                placeholder="/path/to/videos"
                disabled={isScanning}
                className="min-w-0 flex-1 rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none disabled:opacity-50"
                data-testid="scan-directory-input"
              />
              <button
                type="button"
                onClick={() => setShowBrowser(true)}
                disabled={isScanning}
                className="shrink-0 rounded border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 disabled:opacity-50"
                data-testid="scan-browse-button"
              >
                Browse
              </button>
            </div>
          </div>

          <div className="mb-4">
            <label className="flex items-center gap-2 text-sm text-gray-400">
              <input
                type="checkbox"
                checked={recursive}
                onChange={(e) => setRecursive(e.target.checked)}
                disabled={isScanning}
                data-testid="scan-recursive"
              />
              Scan subdirectories
            </label>
          </div>

          {isScanning && (
            <div className="mb-4" data-testid="scan-progress">
              <div className="mb-1 flex justify-between text-sm text-gray-400">
                <span>{scanStatus === 'cancelling' ? 'Cancelling...' : 'Scanning...'}</span>
                {progress !== null && (
                  <span>{Math.round(progress * 100)}%</span>
                )}
              </div>
              <div className="h-2 overflow-hidden rounded bg-gray-800">
                <div
                  className="h-full bg-blue-500 transition-all"
                  style={{ width: `${(progress ?? 0) * 100}%` }}
                />
              </div>
            </div>
          )}

          {scanStatus === 'complete' && (
            <div
              className="mb-4 rounded border border-green-700 bg-green-900/50 p-3 text-sm text-green-200"
              data-testid="scan-complete"
            >
              Scan complete! Videos have been added to your library.
            </div>
          )}

          {scanStatus === 'cancelled' && (
            <div
              className="mb-4 rounded border border-yellow-700 bg-yellow-900/50 p-3 text-sm text-yellow-200"
              data-testid="scan-cancelled"
            >
              Scan cancelled. Partial results have been saved.
            </div>
          )}

          {scanStatus === 'error' && (
            <div
              className="mb-4 rounded border border-red-700 bg-red-900/50 p-3 text-sm text-red-200"
              data-testid="scan-error"
            >
              {errorMessage}
            </div>
          )}

          <div className="flex justify-end gap-2">
            {isScanning && (
              <button
                type="button"
                onClick={handleCancel}
                disabled={scanStatus === 'cancelling'}
                className="rounded border border-red-700 px-4 py-2 text-sm text-red-300 hover:bg-red-900/50 disabled:opacity-50"
                data-testid="scan-abort"
              >
                {scanStatus === 'cancelling' ? 'Cancelling...' : 'Abort Scan'}
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              disabled={isScanning}
              className="rounded border border-gray-700 px-4 py-2 text-sm text-gray-300 hover:bg-gray-800 disabled:opacity-50"
              data-testid="scan-cancel"
            >
              {scanStatus === 'complete' || scanStatus === 'cancelled' ? 'Close' : 'Cancel'}
            </button>
            {scanStatus !== 'complete' && scanStatus !== 'cancelled' && (
              <button
                type="submit"
                disabled={!directory.trim() || isScanning}
                className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                data-testid="scan-submit"
              >
                {isScanning ? 'Scanning...' : 'Start Scan'}
              </button>
            )}
          </div>
        </form>
      </div>

      {showBrowser && (
        <DirectoryBrowser
          initialPath={directory || undefined}
          onSelect={(path) => {
            setDirectory(path)
            setShowBrowser(false)
          }}
          onCancel={() => setShowBrowser(false)}
        />
      )}
    </div>
  )
}
