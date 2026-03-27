import { useEffect, useState, useCallback } from 'react'
import { usePreviewStore } from '../stores/previewStore'
import type { BufferRange } from './PreviewPlayer'

export interface PreviewStatusProps {
  /** Ref to the video element for reading buffered data. */
  videoRef: React.RefObject<HTMLVideoElement | null>
}

/**
 * Real-time preview status display.
 *
 * Shows seek latency (ms), buffer amount as a visual bar, and
 * generation progress during preview creation. Updates at ~4Hz
 * via the video element's timeupdate event.
 */
export default function PreviewStatus({ videoRef }: PreviewStatusProps) {
  const status = usePreviewStore((s) => s.status)
  const progress = usePreviewStore((s) => s.progress)
  const duration = usePreviewStore((s) => s.duration)

  const [seekLatency, setSeekLatency] = useState<number | null>(null)
  const [bufferRanges, setBufferRanges] = useState<BufferRange[]>([])

  // Track seek latency: measure time between 'seeking' and 'seeked' events
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    let seekStart = 0

    const onSeeking = () => {
      seekStart = performance.now()
    }
    const onSeeked = () => {
      if (seekStart > 0) {
        setSeekLatency(Math.round(performance.now() - seekStart))
        seekStart = 0
      }
    }

    video.addEventListener('seeking', onSeeking)
    video.addEventListener('seeked', onSeeked)
    return () => {
      video.removeEventListener('seeking', onSeeking)
      video.removeEventListener('seeked', onSeeked)
    }
  }, [videoRef])

  // Update buffer ranges at timeupdate frequency (~4Hz)
  const updateBuffers = useCallback(() => {
    const video = videoRef.current
    if (!video) return
    const ranges: BufferRange[] = []
    for (let i = 0; i < video.buffered.length; i++) {
      ranges.push({
        start: video.buffered.start(i),
        end: video.buffered.end(i),
      })
    }
    setBufferRanges(ranges)
  }, [videoRef])

  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    video.addEventListener('timeupdate', updateBuffers)
    video.addEventListener('progress', updateBuffers)
    return () => {
      video.removeEventListener('timeupdate', updateBuffers)
      video.removeEventListener('progress', updateBuffers)
    }
  }, [videoRef, updateBuffers])

  // Calculate total buffered seconds
  const totalBuffered = bufferRanges.reduce(
    (sum, r) => sum + (r.end - r.start),
    0,
  )
  const bufferPercent = duration > 0 ? Math.min(100, (totalBuffered / duration) * 100) : 0

  return (
    <div
      className="flex items-center gap-4 text-xs text-gray-400"
      data-testid="preview-status"
    >
      {/* Generation progress during creation */}
      {status === 'generating' && (
        <span data-testid="generation-progress">
          Generating: {Math.round(progress * 100)}%
        </span>
      )}

      {/* Seek latency */}
      {seekLatency !== null && (
        <span data-testid="seek-latency">
          Seek: {seekLatency}ms
        </span>
      )}

      {/* Buffer indicator */}
      <div
        className="flex items-center gap-1"
        data-testid="buffer-indicator"
      >
        <span>Buffer:</span>
        <div className="h-2 w-20 overflow-hidden rounded bg-gray-700">
          <div
            className="h-full bg-green-500 transition-all"
            style={{ width: `${bufferPercent}%` }}
            data-testid="buffer-bar"
          />
        </div>
        <span data-testid="buffer-seconds">
          {totalBuffered.toFixed(1)}s
        </span>
      </div>
    </div>
  )
}
