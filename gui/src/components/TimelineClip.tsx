import type { TimelineClip as ClipType } from '../types/timeline'
import { timeToPixel } from '../utils/timeline'

interface TimelineClipProps {
  clip: ClipType
  zoom: number
  scrollOffset: number
  isSelected: boolean
  onSelect: (clipId: string) => void
}

/** Renders a single clip on a timeline track with position-accurate placement. */
export default function TimelineClip({ clip, zoom, scrollOffset, isSelected, onSelect }: TimelineClipProps) {
  const start = clip.timeline_start ?? 0
  const end = clip.timeline_end ?? start + (clip.out_point - clip.in_point)
  const duration = end - start

  const left = timeToPixel(start, zoom, scrollOffset)
  const right = timeToPixel(end, zoom, scrollOffset)
  const width = right - left

  return (
    <div
      data-testid={`clip-${clip.id}`}
      className={`absolute top-0.5 bottom-0.5 flex cursor-pointer items-center overflow-hidden rounded text-xs ${
        isSelected
          ? 'border-2 border-blue-400 bg-blue-700/80'
          : 'border border-gray-600 bg-indigo-800/70 hover:bg-indigo-700/80'
      }`}
      style={{ left: `${left}px`, width: `${width}px` }}
      onClick={() => onSelect(clip.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onSelect(clip.id)
        }
      }}
      aria-selected={isSelected}
    >
      <span
        data-testid={`clip-duration-${clip.id}`}
        className="truncate px-1 text-gray-200"
      >
        {duration.toFixed(1)}s
      </span>
    </div>
  )
}
