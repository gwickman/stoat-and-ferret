import { useCallback } from 'react'

export interface VolumeSliderProps {
  /** Volume level from 0 to 1. */
  volume: number
  /** Whether audio is muted. */
  muted: boolean
  /** Called when volume changes. */
  onVolumeChange: (volume: number) => void
  /** Called when mute state toggles. */
  onMuteToggle: () => void
}

/**
 * Volume slider with mute toggle button.
 *
 * Range input maps [0, 1] to volume. Mute toggle sets volume to 0
 * visually while preserving the previous level for restore on un-mute.
 */
export default function VolumeSlider({
  volume,
  muted,
  onVolumeChange,
  onMuteToggle,
}: VolumeSliderProps) {
  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onVolumeChange(parseFloat(e.target.value))
    },
    [onVolumeChange],
  )

  const displayVolume = muted ? 0 : volume

  return (
    <div className="flex items-center gap-1" data-testid="volume-container">
      <button
        type="button"
        onClick={onMuteToggle}
        className="rounded p-1 text-gray-400 hover:text-white"
        aria-label={muted ? 'Unmute' : 'Mute'}
        data-testid="mute-btn"
      >
        {muted || volume === 0 ? (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="currentColor"
            className="h-5 w-5"
            aria-hidden="true"
          >
            <path d="M13.5 4.06c0-1.336-1.616-2.005-2.56-1.06l-4.5 4.5H4.508c-1.141 0-2.318.664-2.66 1.905A9.76 9.76 0 0 0 1.5 12c0 .898.121 1.768.35 2.595.341 1.24 1.518 1.905 2.659 1.905h1.93l4.5 4.5c.945.945 2.561.276 2.561-1.06V4.06ZM17.78 9.22a.75.75 0 1 0-1.06 1.06L18.44 12l-1.72 1.72a.75.75 0 1 0 1.06 1.06l1.72-1.72 1.72 1.72a.75.75 0 1 0 1.06-1.06L20.56 12l1.72-1.72a.75.75 0 1 0-1.06-1.06l-1.72 1.72-1.72-1.72Z" />
          </svg>
        ) : (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="currentColor"
            className="h-5 w-5"
            aria-hidden="true"
          >
            <path d="M13.5 4.06c0-1.336-1.616-2.005-2.56-1.06l-4.5 4.5H4.508c-1.141 0-2.318.664-2.66 1.905A9.76 9.76 0 0 0 1.5 12c0 .898.121 1.768.35 2.595.341 1.24 1.518 1.905 2.659 1.905h1.93l4.5 4.5c.945.945 2.561.276 2.561-1.06V4.06ZM18.584 5.106a.75.75 0 0 1 1.06 0c3.808 3.807 3.808 9.98 0 13.788a.75.75 0 0 1-1.06-1.06 8.25 8.25 0 0 0 0-11.668.75.75 0 0 1 0-1.06Z" />
            <path d="M15.932 7.757a.75.75 0 0 1 1.061 0 6 6 0 0 1 0 8.486.75.75 0 0 1-1.06-1.061 4.5 4.5 0 0 0 0-6.364.75.75 0 0 1 0-1.06Z" />
          </svg>
        )}
      </button>
      <input
        type="range"
        min="0"
        max="1"
        step="0.01"
        value={displayVolume}
        onChange={handleChange}
        className="h-1 w-20 cursor-pointer accent-blue-500"
        aria-label="Volume"
        data-testid="volume-slider"
      />
    </div>
  )
}
