import { useEffect, useRef, useCallback } from 'react'
import { usePreviewStore } from '../stores/previewStore'
import { useTimelineStore } from '../stores/timelineStore'

/** Debounce interval in milliseconds. Configurable constant for runtime tuning. */
export const SYNC_DEBOUNCE_MS = 100

/** Minimum position difference (in seconds) that triggers a resync. */
export const SYNC_THRESHOLD_S = 0.5

/**
 * Bidirectional sync between the preview player and timeline playhead.
 *
 * Player → Timeline: updates playheadPosition when video position changes.
 * Timeline → Player: seekFromTimeline seeks the video element.
 * A useRef guard flag prevents infinite update loops.
 */
export function useTimelineSync(
  videoRef: React.RefObject<HTMLVideoElement | null>,
) {
  const isSeeking = useRef(false)
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const position = usePreviewStore((s) => s.position)

  // Player → Timeline: debounced sync of player position to timeline playhead.
  useEffect(() => {
    if (isSeeking.current) return

    debounceTimer.current = setTimeout(() => {
      const playhead = useTimelineStore.getState().playheadPosition
      if (Math.abs(position - playhead) > SYNC_THRESHOLD_S) {
        useTimelineStore.getState().setPlayheadPosition(position)
      }
    }, SYNC_DEBOUNCE_MS)

    return () => {
      if (debounceTimer.current !== null) {
        clearTimeout(debounceTimer.current)
      }
    }
  }, [position])

  // Timeline → Player: seek the video element to the given position.
  const seekFromTimeline = useCallback(
    (pos: number) => {
      const video = videoRef.current
      if (!video) return

      isSeeking.current = true
      video.currentTime = pos
      usePreviewStore.getState().setPosition(pos)
      useTimelineStore.getState().setPlayheadPosition(pos)

      // Reset guard after debounce window to let the seek settle.
      setTimeout(() => {
        isSeeking.current = false
      }, SYNC_DEBOUNCE_MS)
    },
    [videoRef],
  )

  return { seekFromTimeline }
}
