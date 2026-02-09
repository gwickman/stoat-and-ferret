import { useCallback, useEffect, useRef, useState } from 'react'

interface ScanModalProps {
  open: boolean
  onClose: () => void
  onScanComplete: () => void
}

type ScanStatus = 'idle' | 'scanning' | 'complete' | 'error'

interface JobStatus {
  job_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
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
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

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
    }
  }, [open, cleanup])

  useEffect(() => () => cleanup(), [cleanup])

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

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      data-testid="scan-modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget && scanStatus !== 'scanning') onClose()
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
            <input
              id="scan-directory"
              type="text"
              value={directory}
              onChange={(e) => setDirectory(e.target.value)}
              placeholder="/path/to/videos"
              disabled={scanStatus === 'scanning'}
              className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none disabled:opacity-50"
              data-testid="scan-directory-input"
            />
          </div>

          <div className="mb-4">
            <label className="flex items-center gap-2 text-sm text-gray-400">
              <input
                type="checkbox"
                checked={recursive}
                onChange={(e) => setRecursive(e.target.checked)}
                disabled={scanStatus === 'scanning'}
                data-testid="scan-recursive"
              />
              Scan subdirectories
            </label>
          </div>

          {scanStatus === 'scanning' && (
            <div className="mb-4" data-testid="scan-progress">
              <div className="mb-1 flex justify-between text-sm text-gray-400">
                <span>Scanning...</span>
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

          {scanStatus === 'error' && (
            <div
              className="mb-4 rounded border border-red-700 bg-red-900/50 p-3 text-sm text-red-200"
              data-testid="scan-error"
            >
              {errorMessage}
            </div>
          )}

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={scanStatus === 'scanning'}
              className="rounded border border-gray-700 px-4 py-2 text-sm text-gray-300 hover:bg-gray-800 disabled:opacity-50"
              data-testid="scan-cancel"
            >
              {scanStatus === 'complete' ? 'Close' : 'Cancel'}
            </button>
            {scanStatus !== 'complete' && (
              <button
                type="submit"
                disabled={!directory.trim() || scanStatus === 'scanning'}
                className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                data-testid="scan-submit"
              >
                {scanStatus === 'scanning' ? 'Scanning...' : 'Start Scan'}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}
