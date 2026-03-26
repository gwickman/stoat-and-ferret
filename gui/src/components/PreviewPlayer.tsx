import { useEffect, useRef, useCallback, useState } from 'react'
import Hls from 'hls.js'

/** Buffer range reported by the video element. */
export interface BufferRange {
  start: number
  end: number
}

export interface PreviewPlayerProps {
  /** HLS manifest URL, or null/undefined when not yet available. */
  manifestUrl: string | null | undefined
  /** Called when buffer state changes. */
  onBufferUpdate?: (ranges: BufferRange[]) => void
  /** Called on playback error. */
  onError?: (message: string) => void
}

/** HLS.js VOD configuration per NFR-002. */
const HLS_CONFIG: Partial<Hls['config']> = {
  lowLatencyMode: false,
  startPosition: -1,
  maxBufferLength: 30,
  enableWorker: true,
}

/**
 * HLS video player with Safari native fallback.
 *
 * Uses HLS.js for Chrome/Firefox and native video element for Safari.
 * Includes fatal error recovery and buffer tracking via video.buffered.
 */
export default function PreviewPlayer({
  manifestUrl,
  onBufferUpdate,
  onError,
}: PreviewPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const hlsRef = useRef<Hls | null>(null)
  const [usingSafari, setUsingSafari] = useState(false)

  const getBufferRanges = useCallback((): BufferRange[] => {
    const video = videoRef.current
    if (!video) return []
    const ranges: BufferRange[] = []
    for (let i = 0; i < video.buffered.length; i++) {
      ranges.push({
        start: video.buffered.start(i),
        end: video.buffered.end(i),
      })
    }
    return ranges
  }, [])

  // Buffer tracking via video.buffered (universal for both paths)
  useEffect(() => {
    const video = videoRef.current
    if (!video || !onBufferUpdate) return

    const handleProgress = () => {
      onBufferUpdate(getBufferRanges())
    }

    video.addEventListener('progress', handleProgress)
    return () => video.removeEventListener('progress', handleProgress)
  }, [onBufferUpdate, getBufferRanges])

  // Safari error handler
  useEffect(() => {
    if (!usingSafari) return
    const video = videoRef.current
    if (!video || !onError) return

    const handleError = () => {
      onError('Video playback error')
    }

    video.addEventListener('error', handleError)
    return () => video.removeEventListener('error', handleError)
  }, [usingSafari, onError])

  // HLS.js or Safari native initialization
  useEffect(() => {
    const video = videoRef.current
    if (!video || !manifestUrl) return

    // HLS.js path (Chrome/Firefox)
    if (Hls.isSupported()) {
      const hls = new Hls(HLS_CONFIG)
      hlsRef.current = hls

      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (!data.fatal) return

        switch (data.type) {
          case Hls.ErrorTypes.MEDIA_ERROR:
            hls.recoverMediaError()
            break
          case Hls.ErrorTypes.NETWORK_ERROR:
            hls.startLoad(-1)
            break
          default:
            hls.destroy()
            onError?.(`Fatal playback error: ${data.details}`)
            break
        }
      })

      hls.loadSource(manifestUrl)
      hls.attachMedia(video)

      return () => {
        hls.destroy()
        hlsRef.current = null
      }
    }

    // Safari native HLS fallback
    if (video.canPlayType('application/vnd.apple.mpegurl')) {
      setUsingSafari(true)
      video.src = manifestUrl

      return () => {
        video.removeAttribute('src')
        video.load()
        setUsingSafari(false)
      }
    }

    onError?.('HLS playback not supported in this browser')
  }, [manifestUrl, onError])

  // Loading state when manifest not ready
  if (!manifestUrl) {
    return (
      <div
        data-testid="preview-player-loading"
        className="flex h-64 items-center justify-center rounded border border-gray-700 bg-gray-900"
      >
        <div className="flex flex-col items-center gap-2">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-600 border-t-blue-500" />
          <p className="text-sm text-gray-400">Waiting for preview...</p>
        </div>
      </div>
    )
  }

  return (
    <div data-testid="preview-player-container">
      <video
        ref={videoRef}
        data-testid="preview-player-video"
        className="w-full rounded bg-black"
        playsInline
      />
    </div>
  )
}
