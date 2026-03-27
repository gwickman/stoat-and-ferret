import { useCallback } from 'react'

export interface ProgressBarProps {
  /** Current playback position in seconds. */
  currentTime: number
  /** Total duration in seconds. */
  duration: number
  /** Called when user clicks to seek. */
  onSeek: (time: number) => void
}

/** Format seconds as mm:ss or hh:mm:ss for durations >= 1 hour. */
export function formatTime(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  const pad = (n: number) => String(n).padStart(2, '0')
  return h > 0 ? `${h}:${pad(m)}:${pad(sec)}` : `${m}:${pad(sec)}`
}

/**
 * Clickable progress bar showing current playback position.
 *
 * Displays a filled bar proportional to currentTime/duration and
 * handles click-to-seek by calculating position from click offset.
 */
export default function ProgressBar({
  currentTime,
  duration,
  onSeek,
}: ProgressBarProps) {
  const fraction = duration > 0 ? currentTime / duration : 0

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (duration <= 0) return
      const rect = e.currentTarget.getBoundingClientRect()
      const x = e.clientX - rect.left
      const ratio = Math.max(0, Math.min(1, x / rect.width))
      onSeek(ratio * duration)
    },
    [duration, onSeek],
  )

  return (
    <div className="flex items-center gap-2" data-testid="progress-bar-container">
      <span className="text-xs text-gray-400 tabular-nums" data-testid="time-current">
        {formatTime(currentTime)}
      </span>
      <div
        role="progressbar"
        aria-valuenow={Math.round(currentTime)}
        aria-valuemin={0}
        aria-valuemax={Math.round(duration)}
        aria-label="Playback progress"
        className="relative h-2 flex-1 cursor-pointer rounded bg-gray-700"
        data-testid="progress-bar-track"
        onClick={handleClick}
      >
        <div
          className="absolute inset-y-0 left-0 rounded bg-blue-500 transition-[width] duration-100"
          style={{ width: `${Math.min(100, fraction * 100)}%` }}
          data-testid="progress-bar-fill"
        />
      </div>
      <span className="text-xs text-gray-400 tabular-nums" data-testid="time-duration">
        {formatTime(duration)}
      </span>
    </div>
  )
}
