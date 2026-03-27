import { useEffect, useCallback, useRef, useState } from 'react'
import { usePreviewStore } from '../stores/previewStore'
import ProgressBar from './ProgressBar'
import VolumeSlider from './VolumeSlider'

export interface PlayerControlsProps {
  /** Ref to the video element for direct playback control. */
  videoRef: React.RefObject<HTMLVideoElement | null>
}

const SKIP_SECONDS = 5
const VOLUME_STEP = 0.1

/**
 * Transport controls for video playback.
 *
 * Provides play/pause, skip ±5s, progress bar with seek, volume slider
 * with mute toggle, time display, and keyboard accessibility (Space,
 * arrow keys) meeting WCAG AA.
 */
export default function PlayerControls({ videoRef }: PlayerControlsProps) {
  const [playing, setPlaying] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const position = usePreviewStore((s) => s.position)
  const duration = usePreviewStore((s) => s.duration)
  const volume = usePreviewStore((s) => s.volume)
  const muted = usePreviewStore((s) => s.muted)
  const setPosition = usePreviewStore((s) => s.setPosition)
  const setVolume = usePreviewStore((s) => s.setVolume)
  const setMuted = usePreviewStore((s) => s.setMuted)

  // Sync video element state to store
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const onTimeUpdate = () => {
      usePreviewStore.setState({ position: video.currentTime })
    }
    const onDurationChange = () => {
      usePreviewStore.setState({ duration: video.duration || 0 })
    }
    const onPlay = () => setPlaying(true)
    const onPause = () => setPlaying(false)

    video.addEventListener('timeupdate', onTimeUpdate)
    video.addEventListener('durationchange', onDurationChange)
    video.addEventListener('play', onPlay)
    video.addEventListener('pause', onPause)

    // Initialize from current video state
    if (video.duration) {
      usePreviewStore.setState({ duration: video.duration })
    }
    setPlaying(!video.paused)

    return () => {
      video.removeEventListener('timeupdate', onTimeUpdate)
      video.removeEventListener('durationchange', onDurationChange)
      video.removeEventListener('play', onPlay)
      video.removeEventListener('pause', onPause)
    }
  }, [videoRef])

  const togglePlay = useCallback(() => {
    const video = videoRef.current
    if (!video) return
    if (video.paused) {
      video.play().catch(() => {})
    } else {
      video.pause()
    }
  }, [videoRef])

  const skip = useCallback(
    (offset: number) => {
      const video = videoRef.current
      if (!video) return
      const newTime = Math.max(0, Math.min(video.currentTime + offset, video.duration || 0))
      video.currentTime = newTime
      setPosition(newTime)
    },
    [videoRef, setPosition],
  )

  const handleSeek = useCallback(
    (time: number) => {
      const video = videoRef.current
      if (!video) return
      video.currentTime = time
      setPosition(time)
    },
    [videoRef, setPosition],
  )

  const handleVolumeChange = useCallback(
    (v: number) => {
      const video = videoRef.current
      setVolume(v)
      if (video) {
        video.volume = Math.max(0, Math.min(1, v))
      }
      if (muted && v > 0) {
        setMuted(false)
        if (video) video.muted = false
      }
    },
    [videoRef, setVolume, muted, setMuted],
  )

  const previousVolumeRef = useRef(volume)
  // Track non-zero volume for mute restore
  useEffect(() => {
    if (volume > 0) {
      previousVolumeRef.current = volume
    }
  }, [volume])

  const handleMuteToggle = useCallback(() => {
    const video = videoRef.current
    const newMuted = !muted
    setMuted(newMuted)
    if (video) video.muted = newMuted
    if (newMuted) {
      // Store current volume for restore
      previousVolumeRef.current = volume > 0 ? volume : previousVolumeRef.current
    } else {
      // Restore previous volume
      const restored = previousVolumeRef.current || 1
      setVolume(restored)
      if (video) video.volume = restored
    }
  }, [videoRef, muted, volume, setMuted, setVolume])

  // Keyboard accessibility
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      switch (e.key) {
        case ' ':
          e.preventDefault()
          togglePlay()
          break
        case 'ArrowLeft':
          e.preventDefault()
          skip(-SKIP_SECONDS)
          break
        case 'ArrowRight':
          e.preventDefault()
          skip(SKIP_SECONDS)
          break
        case 'ArrowUp':
          e.preventDefault()
          handleVolumeChange(Math.min(1, volume + VOLUME_STEP))
          break
        case 'ArrowDown':
          e.preventDefault()
          handleVolumeChange(Math.max(0, volume - VOLUME_STEP))
          break
      }
    },
    [togglePlay, skip, handleVolumeChange, volume],
  )

  return (
    <div
      ref={containerRef}
      className="flex flex-col gap-2 rounded-b border border-t-0 border-gray-700 bg-gray-900 p-3"
      data-testid="player-controls"
      tabIndex={0}
      role="toolbar"
      aria-label="Video player controls"
      onKeyDown={handleKeyDown}
    >
      <ProgressBar currentTime={position} duration={duration} onSeek={handleSeek} />
      <div className="flex items-center gap-2">
        {/* Skip backward */}
        <button
          type="button"
          onClick={() => skip(-SKIP_SECONDS)}
          className="rounded p-1 text-gray-400 hover:text-white"
          aria-label="Skip backward 5 seconds"
          data-testid="skip-back-btn"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="currentColor"
            className="h-5 w-5"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M12 2.25c-5.385 0-9.75 4.365-9.75 9.75s4.365 9.75 9.75 9.75 9.75-4.365 9.75-9.75S17.385 2.25 12 2.25Zm-4.28 9.22a.75.75 0 0 0 0 1.06l3 3a.75.75 0 1 0 1.06-1.06l-1.72-1.72h5.69a.75.75 0 0 0 0-1.5h-5.69l1.72-1.72a.75.75 0 0 0-1.06-1.06l-3 3Z"
              clipRule="evenodd"
            />
          </svg>
        </button>

        {/* Play/Pause */}
        <button
          type="button"
          onClick={togglePlay}
          className="rounded p-1 text-gray-400 hover:text-white"
          aria-label={playing ? 'Pause' : 'Play'}
          data-testid="play-pause-btn"
        >
          {playing ? (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="currentColor"
              className="h-6 w-6"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M6.75 5.25a.75.75 0 0 1 .75-.75H9a.75.75 0 0 1 .75.75v13.5a.75.75 0 0 1-.75.75H7.5a.75.75 0 0 1-.75-.75V5.25Zm7.5 0A.75.75 0 0 1 15 4.5h1.5a.75.75 0 0 1 .75.75v13.5a.75.75 0 0 1-.75.75H15a.75.75 0 0 1-.75-.75V5.25Z"
                clipRule="evenodd"
              />
            </svg>
          ) : (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="currentColor"
              className="h-6 w-6"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M4.5 5.653c0-1.427 1.529-2.33 2.779-1.643l11.54 6.347c1.295.712 1.295 2.573 0 3.286L7.28 19.99c-1.25.687-2.779-.217-2.779-1.643V5.653Z"
                clipRule="evenodd"
              />
            </svg>
          )}
        </button>

        {/* Skip forward */}
        <button
          type="button"
          onClick={() => skip(SKIP_SECONDS)}
          className="rounded p-1 text-gray-400 hover:text-white"
          aria-label="Skip forward 5 seconds"
          data-testid="skip-fwd-btn"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="currentColor"
            className="h-5 w-5"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M12 2.25c-5.385 0-9.75 4.365-9.75 9.75s4.365 9.75 9.75 9.75 9.75-4.365 9.75-9.75S17.385 2.25 12 2.25Zm4.28 10.28a.75.75 0 0 0 0-1.06l-3-3a.75.75 0 1 0-1.06 1.06l1.72 1.72H8.25a.75.75 0 0 0 0 1.5h5.69l-1.72 1.72a.75.75 0 1 0 1.06 1.06l3-3Z"
              clipRule="evenodd"
            />
          </svg>
        </button>

        <div className="flex-1" />

        {/* Volume */}
        <VolumeSlider
          volume={volume}
          muted={muted}
          onVolumeChange={handleVolumeChange}
          onMuteToggle={handleMuteToggle}
        />
      </div>
    </div>
  )
}
