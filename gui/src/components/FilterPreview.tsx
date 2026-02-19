import { useState } from 'react'
import { useEffectPreviewStore } from '../stores/effectPreviewStore'

/** Known FFmpeg filter names for syntax highlighting. */
const FILTER_NAMES = [
  'drawtext',
  'setpts',
  'atempo',
  'amix',
  'volume',
  'afade',
  'fade',
  'xfade',
  'acrossfade',
  'asplit',
  'anull',
  'sidechaincompress',
]

/**
 * Apply simple regex-based syntax highlighting to an FFmpeg filter string.
 *
 * - Pad labels like `[0:v]`, `[out]` get a distinct color.
 * - Filter names get a keyword color.
 * - Everything else stays default.
 */
export function highlightFilter(filter: string): React.ReactNode[] {
  // Match pad labels [xxx] or filter names at word boundaries
  const pattern = new RegExp(
    `(\\[[^\\]]+\\])|(\\b(?:${FILTER_NAMES.join('|')})\\b)`,
    'g',
  )

  const parts: React.ReactNode[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = pattern.exec(filter)) !== null) {
    // Text before this match
    if (match.index > lastIndex) {
      parts.push(filter.slice(lastIndex, match.index))
    }

    if (match[1]) {
      // Pad label
      parts.push(
        <span key={match.index} className="text-cyan-400" data-testid="pad-label">
          {match[1]}
        </span>,
      )
    } else if (match[2]) {
      // Filter name
      parts.push(
        <span key={match.index} className="text-yellow-300" data-testid="filter-name">
          {match[2]}
        </span>,
      )
    }

    lastIndex = match.index + match[0].length
  }

  // Remaining text after last match
  if (lastIndex < filter.length) {
    parts.push(filter.slice(lastIndex))
  }

  return parts
}

/**
 * Monospace panel displaying the live FFmpeg filter string preview
 * with syntax highlighting and copy-to-clipboard.
 */
export default function FilterPreview() {
  const { filterString, isLoading, error } = useEffectPreviewStore()
  const [copied, setCopied] = useState(false)

  if (!filterString && !isLoading && !error) {
    return null
  }

  async function handleCopy() {
    await navigator.clipboard.writeText(filterString)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div data-testid="filter-preview" className="mt-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-semibold text-white">Filter Preview</h3>
        {filterString && (
          <button
            type="button"
            onClick={handleCopy}
            className="rounded bg-gray-700 px-2 py-1 text-xs text-gray-300 hover:bg-gray-600"
            data-testid="copy-button"
            aria-label="Copy filter string"
          >
            {copied ? 'Copied!' : 'Copy'}
          </button>
        )}
      </div>

      {isLoading && (
        <div
          className="rounded border border-gray-700 bg-gray-900 p-3"
          data-testid="preview-loading"
        >
          <span className="text-sm text-gray-400">Generating preview...</span>
        </div>
      )}

      {error && (
        <div
          className="rounded border border-red-700 bg-red-900/50 p-3"
          data-testid="preview-error"
        >
          <span className="text-sm text-red-400">{error}</span>
        </div>
      )}

      {filterString && !isLoading && (
        <pre
          className="overflow-x-auto rounded border border-gray-700 bg-gray-900 p-3 font-mono text-sm text-gray-200"
          data-testid="filter-string"
        >
          {highlightFilter(filterString)}
        </pre>
      )}
    </div>
  )
}
