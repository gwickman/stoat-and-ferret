import { lazy, Suspense, useEffect } from 'react'
import { usePreviewStore } from '../stores/previewStore'
import { useProjectStore } from '../stores/projectStore'

const PreviewPlayer = lazy(() => import('../components/PreviewPlayer'))

export default function PreviewPage() {
  const selectedProjectId = useProjectStore((s) => s.selectedProjectId)
  const sessionId = usePreviewStore((s) => s.sessionId)
  const status = usePreviewStore((s) => s.status)
  const error = usePreviewStore((s) => s.error)
  const progress = usePreviewStore((s) => s.progress)
  const connect = usePreviewStore((s) => s.connect)

  // Connect to existing session if a project is selected and no session active
  useEffect(() => {
    if (!selectedProjectId || sessionId) return
    let active = true

    async function checkExistingSession() {
      try {
        const res = await fetch(
          `/api/v1/projects/${selectedProjectId}/preview/start`,
          { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ quality: usePreviewStore.getState().quality }) },
        )
        if (!res.ok) return
        const data = await res.json()
        if (active) {
          usePreviewStore.setState({
            sessionId: data.session_id,
            status: 'generating',
          })
        }
      } catch {
        // No existing session — that's fine
      }
    }

    checkExistingSession()
    return () => { active = false }
  }, [selectedProjectId, sessionId])

  return (
    <div className="p-6" data-testid="preview-page">
      <h2 className="mb-4 text-2xl font-semibold">Preview</h2>

      {!selectedProjectId && (
        <p className="text-gray-400" data-testid="no-project-message">
          Select a project to preview.
        </p>
      )}

      {selectedProjectId && !sessionId && status !== 'initializing' && (
        <div data-testid="no-session">
          <p className="mb-4 text-gray-400">No active preview session.</p>
          <button
            type="button"
            data-testid="start-preview-btn"
            onClick={() => connect(selectedProjectId)}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
          >
            Start Preview
          </button>
        </div>
      )}

      {status === 'initializing' && (
        <p className="text-gray-400" data-testid="status-initializing">
          Initializing preview session…
        </p>
      )}

      {status === 'generating' && (
        <div data-testid="status-generating">
          <p className="mb-2 text-gray-400">Generating preview…</p>
          <div className="h-2 w-64 overflow-hidden rounded bg-gray-700">
            <div
              className="h-full bg-blue-500 transition-all"
              style={{ width: `${Math.round(progress * 100)}%` }}
              data-testid="progress-bar"
            />
          </div>
          <span className="text-xs text-gray-500">{Math.round(progress * 100)}%</span>
        </div>
      )}

      {status === 'ready' && sessionId && (
        <Suspense
          fallback={
            <div data-testid="player-suspense-fallback" className="flex h-64 items-center justify-center rounded border border-gray-700 bg-gray-900">
              <p className="text-gray-400">Loading player...</p>
            </div>
          }
        >
          <PreviewPlayer
            manifestUrl={`/api/v1/preview/${sessionId}/manifest.m3u8`}
            onError={(msg) => usePreviewStore.getState().setError(msg)}
          />
        </Suspense>
      )}

      {status === 'error' && error && (
        <div data-testid="error-message" className="rounded border border-red-800 bg-red-900/30 p-4">
          <p className="text-red-400">Preview error: {error}</p>
          {selectedProjectId && (
            <button
              type="button"
              data-testid="retry-preview-btn"
              onClick={() => connect(selectedProjectId)}
              className="mt-2 rounded bg-red-700 px-3 py-1 text-sm text-white hover:bg-red-600"
            >
              Retry
            </button>
          )}
        </div>
      )}

      {status === 'expired' && (
        <div data-testid="status-expired">
          <p className="mb-2 text-gray-400">Preview session expired.</p>
          {selectedProjectId && (
            <button
              type="button"
              data-testid="restart-preview-btn"
              onClick={() => connect(selectedProjectId)}
              className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
            >
              Restart Preview
            </button>
          )}
        </div>
      )}
    </div>
  )
}
