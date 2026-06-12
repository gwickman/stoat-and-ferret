import { useState } from 'react'

interface RazorToolProps {
  projectId: string
  clipId: string
  splitFrame: number
  onSplitComplete?: (clipAId: string, clipBId: string) => void
  disabled?: boolean
}

/**
 * Razor/split affordance — calls POST /clips/{id}/split at the current playhead frame.
 * FR-004-AC-2: GUI razor affordance (deferred_post_merge — requires headed UAT to verify).
 */
export default function RazorTool({
  projectId,
  clipId,
  splitFrame,
  onSplitComplete,
  disabled = false,
}: RazorToolProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSplit = async () => {
    if (disabled || isLoading) return
    setIsLoading(true)
    setError(null)

    try {
      const resp = await fetch(
        `/api/v1/projects/${projectId}/clips/${clipId}/split`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ split_frame: splitFrame }),
        },
      )

      if (!resp.ok) {
        const detail = await resp.json().catch(() => ({}))
        const msg =
          detail?.detail?.error === 'invalid_split_frame'
            ? `Split frame ${splitFrame} is outside clip bounds`
            : `Split failed: ${resp.status}`
        setError(msg)
        return
      }

      const data = await resp.json()
      onSplitComplete?.(data.clip_a.id, data.clip_b.id)
    } catch (err) {
      setError('Split request failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex items-center gap-2">
      <button
        data-testid="razor-tool-button"
        type="button"
        onClick={handleSplit}
        disabled={disabled || isLoading}
        title={`Split clip at frame ${splitFrame}`}
        className="flex items-center gap-1 rounded px-2 py-1 text-xs font-medium
          bg-slate-700 text-slate-200 hover:bg-slate-600 disabled:opacity-50
          disabled:cursor-not-allowed transition-colors"
        aria-label={`Split clip at frame ${splitFrame}`}
      >
        {isLoading ? (
          <span aria-hidden="true">⟳</span>
        ) : (
          <span aria-hidden="true">✂</span>
        )}
        <span>{isLoading ? 'Splitting…' : 'Split'}</span>
      </button>
      {error && (
        <span
          data-testid="razor-tool-error"
          className="text-xs text-red-400"
          role="alert"
        >
          {error}
        </span>
      )}
    </div>
  )
}
