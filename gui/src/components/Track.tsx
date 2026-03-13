import type { Track as TrackType } from '../types/timeline'
import TimelineClip from './TimelineClip'

interface TrackProps {
  track: TrackType
  zoom: number
  scrollOffset: number
  selectedClipId: string | null
  onSelectClip: (clipId: string) => void
}

/** Renders a single timeline track with label and clips. */
export default function Track({ track, zoom, scrollOffset, selectedClipId, onSelectClip }: TrackProps) {
  return (
    <div
      data-testid={`track-${track.id}`}
      className="flex h-12 border-b border-gray-700"
      style={{ order: track.z_index }}
    >
      <div
        data-testid={`track-label-${track.id}`}
        className="flex w-32 shrink-0 items-center border-r border-gray-700 bg-gray-800 px-2 text-xs text-gray-300"
      >
        <span className="truncate">{track.label}</span>
        {track.muted && (
          <span className="ml-1 text-gray-500" data-testid={`track-muted-${track.id}`}>
            M
          </span>
        )}
        {track.locked && (
          <span className="ml-1 text-gray-500" data-testid={`track-locked-${track.id}`}>
            L
          </span>
        )}
      </div>
      <div
        data-testid={`track-content-${track.id}`}
        className="relative flex-1 bg-gray-900"
      >
        {track.clips.map((clip) => (
          <TimelineClip
            key={clip.id}
            clip={clip}
            zoom={zoom}
            scrollOffset={scrollOffset}
            isSelected={clip.id === selectedClipId}
            onSelect={onSelectClip}
          />
        ))}
      </div>
    </div>
  )
}
