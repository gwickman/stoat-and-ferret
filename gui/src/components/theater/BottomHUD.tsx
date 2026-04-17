import PlayerControls from '../PlayerControls'
import { useRenderStore } from '../../stores/renderStore'

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
 * progress bar with percentage and ETA, driven by renderStore state.
 */
export default function BottomHUD({ videoRef }: BottomHUDProps) {
  const activeJob = useRenderStore((s) => s.jobs.find((j) => j.status === 'running') ?? null)
  const progress = activeJob?.progress ?? null
  const etaSeconds = activeJob?.eta_seconds ?? null
  const speedRatio = activeJob?.speed_ratio ?? null
  const frameCount = activeJob?.frame_count ?? null
  const fps = activeJob?.fps ?? null
  const encoderName = activeJob?.encoder_name ?? null
  const encoderType = activeJob?.encoder_type ?? null

  return (
    <div
      data-testid="theater-bottom-hud"
      className="pointer-events-auto absolute right-0 bottom-0 left-0 bg-gradient-to-t from-black/70 to-transparent px-4 pt-6 pb-3"
    >
      {progress !== null && (
        <div data-testid="render-progress" className="mb-2 flex items-center gap-2">
          <div className="h-1.5 flex-1 overflow-hidden rounded bg-gray-700">
            <div
              className="h-full bg-green-500 transition-[width] duration-200"
              style={{ width: `${Math.min(100, Math.round(progress * 100))}%` }}
            />
          </div>
          <span data-testid="render-stats" className="text-xs text-gray-300">
            {Math.round(progress * 100)}%
            {' — '}
            {etaSeconds !== null ? `ETA ${formatEta(etaSeconds)}` : 'Calculating...'}
            {speedRatio !== null && (
              <span data-testid="render-speed"> · {speedRatio.toFixed(1)}x</span>
            )}
            {encoderName !== null && (
              <span data-testid="render-encoder">
                {' · '}
                {encoderName}
                {encoderType !== null && (
                  <span data-testid="render-encoder-type"> ({encoderType})</span>
                )}
              </span>
            )}
            {frameCount !== null && (
              <span data-testid="render-frame-count"> · {frameCount}f</span>
            )}
            {fps !== null && (
              <span data-testid="render-fps"> · {fps.toFixed(1)} fps</span>
            )}
          </span>
        </div>
      )}
      <PlayerControls videoRef={videoRef} />
    </div>
  )
}
