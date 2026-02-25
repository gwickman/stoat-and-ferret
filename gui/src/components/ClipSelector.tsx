import type { Clip } from '../hooks/useProjects'

interface ClipSelectorProps {
  clips: Clip[]
  selectedClipId: string | null
  onSelect: (clipId: string) => void
  /** Enable pair-mode for selecting source/target clips. */
  pairMode?: boolean
  /** Selected "from" (source) clip ID in pair-mode. */
  selectedFromId?: string | null
  /** Selected "to" (target) clip ID in pair-mode. */
  selectedToId?: string | null
  /** Callback for pair-mode selection. */
  onSelectPair?: (clipId: string, role: 'from' | 'to') => void
}

/** Renders a list of clips for selection as an effect target. */
export default function ClipSelector({
  clips,
  selectedClipId,
  onSelect,
  pairMode,
  selectedFromId,
  selectedToId,
  onSelectPair,
}: ClipSelectorProps) {
  if (clips.length === 0) {
    return (
      <div data-testid="clip-selector-empty" className="rounded border border-gray-700 p-4">
        <p className="text-sm text-gray-400">No clips in this project. Add clips to get started.</p>
      </div>
    )
  }

  if (pairMode && onSelectPair) {
    return (
      <div data-testid="clip-selector" className="mb-4">
        <h3 className="mb-2 text-lg font-semibold text-white">Select Clip Pair</h3>
        <div className="flex flex-wrap gap-2">
          {clips.map((clip) => {
            const isFrom = clip.id === selectedFromId
            const isTo = clip.id === selectedToId
            let btnClass = 'border-gray-600 bg-gray-800 text-gray-300 hover:border-gray-500'
            if (isFrom) btnClass = 'border-green-500 bg-green-900/50 text-green-300'
            if (isTo) btnClass = 'border-orange-500 bg-orange-900/50 text-orange-300'

            const handleClick = () => {
              if (!selectedFromId) {
                onSelectPair(clip.id, 'from')
              } else if (clip.id === selectedFromId) {
                // Deselect source — noop, reset handled at parent level
                return
              } else {
                onSelectPair(clip.id, 'to')
              }
            }

            return (
              <button
                key={clip.id}
                type="button"
                data-testid={`clip-option-${clip.id}`}
                onClick={handleClick}
                className={`rounded border px-3 py-2 text-sm transition-colors ${btnClass}`}
              >
                {isFrom && (
                  <span className="mr-1 text-xs font-bold text-green-400" data-testid={`clip-from-badge-${clip.id}`}>
                    FROM
                  </span>
                )}
                {isTo && (
                  <span className="mr-1 text-xs font-bold text-orange-400" data-testid={`clip-to-badge-${clip.id}`}>
                    TO
                  </span>
                )}
                <span className="font-medium">{clip.source_video_id}</span>
                <span className="ml-2 text-xs text-gray-400">
                  pos: {clip.timeline_position} | {clip.in_point}–{clip.out_point}
                </span>
              </button>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div data-testid="clip-selector" className="mb-4">
      <h3 className="mb-2 text-lg font-semibold text-white">Select Clip</h3>
      <div className="flex flex-wrap gap-2">
        {clips.map((clip) => {
          const isSelected = clip.id === selectedClipId
          return (
            <button
              key={clip.id}
              type="button"
              data-testid={`clip-option-${clip.id}`}
              onClick={() => onSelect(clip.id)}
              className={`rounded border px-3 py-2 text-sm transition-colors ${
                isSelected
                  ? 'border-blue-500 bg-blue-900/50 text-blue-300'
                  : 'border-gray-600 bg-gray-800 text-gray-300 hover:border-gray-500'
              }`}
            >
              <span className="font-medium">{clip.source_video_id}</span>
              <span className="ml-2 text-xs text-gray-400">
                pos: {clip.timeline_position} | {clip.in_point}–{clip.out_point}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
