import { formatTime } from './ProgressBar'

/** Thumbnail strip sprite sheet metadata for seek preview. */
export interface ThumbnailMetadata {
  columns: number
  frame_count: number
  frame_height: number
  frame_width: number
  interval_seconds: number
  rows: number
  strip_url: string
}

export interface SeekTooltipProps {
  /** Hover time in seconds. */
  hoverTime: number
  /** Total video duration in seconds. */
  duration: number
  /** Thumbnail strip metadata, or null for time-only fallback. */
  thumbnailMetadata: ThumbnailMetadata | null
  /** Mouse X position relative to the progress bar, in pixels. */
  mouseX: number
  /** Width of the progress bar in pixels. */
  barWidth: number
}

/** Calculate frame index and sprite background offset for a hover time. */
export function calculateFrameOffset(
  hoverTime: number,
  metadata: ThumbnailMetadata,
): { frameIndex: number; bgX: number; bgY: number } {
  let frameIndex = Math.floor(hoverTime / metadata.interval_seconds)
  if (frameIndex >= metadata.frame_count) {
    frameIndex = metadata.frame_count - 1
  }
  if (frameIndex < 0) frameIndex = 0
  const col = frameIndex % metadata.columns
  const row = Math.floor(frameIndex / metadata.columns)
  const bgX = -(col * metadata.frame_width) || 0
  const bgY = -(row * metadata.frame_height) || 0
  return { frameIndex, bgX, bgY }
}

/**
 * Tooltip displayed above the progress bar on hover.
 *
 * Shows a thumbnail frame from the sprite sheet when metadata is available,
 * or a time-only display as fallback. Uses absolute positioning to avoid
 * layout reflow.
 */
export default function SeekTooltip({
  hoverTime,
  thumbnailMetadata,
  mouseX,
  barWidth,
}: SeekTooltipProps) {
  const tooltipWidth = thumbnailMetadata ? thumbnailMetadata.frame_width : 60
  const halfTooltip = tooltipWidth / 2
  const clampedX = Math.max(halfTooltip, Math.min(mouseX, barWidth - halfTooltip))

  const offset = thumbnailMetadata
    ? calculateFrameOffset(hoverTime, thumbnailMetadata)
    : null

  return (
    <div
      className="pointer-events-none absolute bottom-full mb-2"
      style={{
        left: `${clampedX}px`,
        transform: 'translateX(-50%)',
      }}
      data-testid="seek-tooltip"
    >
      {thumbnailMetadata && offset ? (
        <div
          className="overflow-hidden rounded border border-gray-600 bg-black"
          style={{
            width: thumbnailMetadata.frame_width,
            height: thumbnailMetadata.frame_height,
          }}
          data-testid="seek-tooltip-thumbnail"
        >
          <div
            style={{
              width: thumbnailMetadata.frame_width,
              height: thumbnailMetadata.frame_height,
              backgroundImage: `url(${thumbnailMetadata.strip_url})`,
              backgroundPosition: `${offset.bgX}px ${offset.bgY}px`,
              backgroundRepeat: 'no-repeat',
            }}
          />
        </div>
      ) : null}
      <div className="mt-1 text-center text-xs text-white" data-testid="seek-tooltip-time">
        {formatTime(hoverTime)}
      </div>
    </div>
  )
}
