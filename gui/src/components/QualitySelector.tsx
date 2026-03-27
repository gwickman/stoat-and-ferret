import { useCallback } from 'react'
import { usePreviewStore, type PreviewQuality } from '../stores/previewStore'
import { useProjectStore } from '../stores/projectStore'

const QUALITY_OPTIONS: { value: PreviewQuality; label: string }[] = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
]

/**
 * Dropdown for selecting preview quality level.
 *
 * Changing quality DELETEs the current preview session and creates
 * a new one at the selected quality via the store's setQuality action.
 */
export default function QualitySelector() {
  const quality = usePreviewStore((s) => s.quality)
  const status = usePreviewStore((s) => s.status)
  const setQuality = usePreviewStore((s) => s.setQuality)
  const selectedProjectId = useProjectStore((s) => s.selectedProjectId)

  const disabled = status === 'generating' || status === 'initializing'

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const newQuality = e.target.value as PreviewQuality
      if (newQuality === quality || !selectedProjectId) return
      setQuality(selectedProjectId, newQuality)
    },
    [quality, selectedProjectId, setQuality],
  )

  return (
    <div className="flex items-center gap-2" data-testid="quality-selector">
      <label
        htmlFor="quality-select"
        className="text-sm text-gray-400"
      >
        Quality
      </label>
      <select
        id="quality-select"
        data-testid="quality-select"
        value={quality}
        onChange={handleChange}
        disabled={disabled}
        className="rounded border border-gray-600 bg-gray-800 px-2 py-1 text-sm text-gray-200 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {QUALITY_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}
