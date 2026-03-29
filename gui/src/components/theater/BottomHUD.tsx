import { useEffect, useState } from 'react'
import PlayerControls from '../PlayerControls'
import { useWebSocket } from '../../hooks/useWebSocket'

interface RenderProgressEvent {
  type: string
  payload: {
    progress: number
    eta_seconds: number | null
  }
}

interface RenderProgressState {
  progress: number
  etaSeconds: number | null
}

function wsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws`
}

function formatEta(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}m ${s}s`
}

export interface BottomHUDProps {
  /** Ref to the video element for playback control. */
  videoRef: React.RefObject<HTMLVideoElement | null>
}

/**
 * Bottom HUD overlay for Theater Mode.
 *
 * Includes full playback controls (reusing PlayerControls) and a render
 * progress bar with percentage and ETA, updated in real-time via
 * RENDER_PROGRESS WebSocket events.
 */
export default function BottomHUD({ videoRef }: BottomHUDProps) {
  const { lastMessage } = useWebSocket(wsUrl())
  const [renderProgress, setRenderProgress] = useState<RenderProgressState | null>(null)

  useEffect(() => {
    if (!lastMessage) return

    try {
      const event: RenderProgressEvent = JSON.parse(lastMessage.data)
      if (event.type !== 'render_progress') return
      setRenderProgress({
        progress: event.payload.progress,
        etaSeconds: event.payload.eta_seconds,
      })
    } catch {
      // Ignore non-JSON messages
    }
  }, [lastMessage])

  return (
    <div
      data-testid="theater-bottom-hud"
      className="pointer-events-auto absolute right-0 bottom-0 left-0 bg-gradient-to-t from-black/70 to-transparent px-4 pt-6 pb-3"
    >
      {renderProgress !== null && (
        <div data-testid="render-progress" className="mb-2 flex items-center gap-2">
          <div className="h-1.5 flex-1 overflow-hidden rounded bg-gray-700">
            <div
              className="h-full bg-green-500 transition-[width] duration-200"
              style={{ width: `${Math.min(100, Math.round(renderProgress.progress * 100))}%` }}
            />
          </div>
          <span className="text-xs text-gray-300">
            {Math.round(renderProgress.progress * 100)}%
            {renderProgress.etaSeconds !== null && ` — ETA ${formatEta(renderProgress.etaSeconds)}`}
          </span>
        </div>
      )}
      <PlayerControls videoRef={videoRef} />
    </div>
  )
}
