import { useEffect, useCallback } from 'react'
import { usePreviewStore } from '../stores/previewStore'

const SKIP_SECONDS = 5

/** Tags that should not trigger theater shortcuts. */
const IGNORED_TAGS = new Set(['INPUT', 'TEXTAREA', 'SELECT'])

export interface UseTheaterShortcutsOptions {
  /** Ref to the video element for playback control. */
  videoRef: React.RefObject<HTMLVideoElement | null>
  /** Callback to exit theater/fullscreen mode. */
  onExit: () => void
  /** Callback to toggle fullscreen on/off. */
  onToggleFullscreen: () => void
  /** Whether shortcuts are active (true only in fullscreen). */
  enabled: boolean
}

/**
 * Keyboard shortcuts scoped to the Theater Mode container.
 *
 * Bindings: Space (play/pause), Escape (exit), F (fullscreen toggle),
 * M (mute), Left/Right (seek ±5s), Home (start), End (end of timeline).
 */
export function useTheaterShortcuts({
  videoRef,
  onExit,
  onToggleFullscreen,
  enabled,
}: UseTheaterShortcutsOptions) {
  const setPosition = usePreviewStore((s) => s.setPosition)
  const setMuted = usePreviewStore((s) => s.setMuted)

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Skip shortcuts when typing in form inputs (FR-007)
      const target = e.target as HTMLElement
      if (IGNORED_TAGS.has(target.tagName)) return

      const video = videoRef.current
      if (!video) return

      switch (e.key) {
        case ' ':
          e.preventDefault()
          if (video.paused) {
            video.play().catch(() => {})
          } else {
            video.pause()
          }
          break

        case 'Escape':
          e.preventDefault()
          onExit()
          break

        case 'f':
        case 'F':
          e.preventDefault()
          onToggleFullscreen()
          break

        case 'm':
        case 'M': {
          e.preventDefault()
          const newMuted = !video.muted
          video.muted = newMuted
          setMuted(newMuted)
          break
        }

        case 'ArrowLeft':
          e.preventDefault()
          video.currentTime = Math.max(0, video.currentTime - SKIP_SECONDS)
          setPosition(video.currentTime)
          break

        case 'ArrowRight':
          e.preventDefault()
          video.currentTime = Math.min(
            video.duration || 0,
            video.currentTime + SKIP_SECONDS,
          )
          setPosition(video.currentTime)
          break

        case 'Home':
          e.preventDefault()
          video.currentTime = 0
          setPosition(0)
          break

        case 'End':
          e.preventDefault()
          video.currentTime = video.duration || 0
          setPosition(video.duration || 0)
          break
      }
    },
    [videoRef, onExit, onToggleFullscreen, setPosition, setMuted],
  )

  useEffect(() => {
    if (!enabled) return
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [enabled, handleKeyDown])
}
