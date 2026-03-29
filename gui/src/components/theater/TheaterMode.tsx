import { useEffect, useRef, useCallback } from 'react'
import { useTheaterStore } from '../../stores/theaterStore'

const HUD_HIDE_DELAY_MS = 3000

interface TheaterModeProps {
  /** Content to render inside the fullscreen container (e.g. PreviewPlayer). */
  children: React.ReactNode
}

/**
 * Fullscreen wrapper with auto-hiding HUD container.
 *
 * Passes through children when not in fullscreen. When fullscreen is active,
 * wraps children in a theater container with mouse-tracking HUD overlay
 * that auto-hides after 3 seconds of inactivity.
 */
export default function TheaterMode({ children }: TheaterModeProps) {
  const isFullscreen = useTheaterStore((s) => s.isFullscreen)
  const isHUDVisible = useTheaterStore((s) => s.isHUDVisible)
  const showHUD = useTheaterStore((s) => s.showHUD)
  const hideHUD = useTheaterStore((s) => s.hideHUD)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearHideTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const startHideTimer = useCallback(() => {
    clearHideTimer()
    timerRef.current = setTimeout(() => {
      hideHUD()
    }, HUD_HIDE_DELAY_MS)
  }, [clearHideTimer, hideHUD])

  const handleMouseMove = useCallback(() => {
    if (!isFullscreen) return
    showHUD()
    startHideTimer()
  }, [isFullscreen, showHUD, startHideTimer])

  // Start the auto-hide timer when entering fullscreen
  useEffect(() => {
    if (isFullscreen) {
      startHideTimer()
    } else {
      clearHideTimer()
    }
  }, [isFullscreen, startHideTimer, clearHideTimer])

  // Cleanup timer on unmount (NFR-001)
  useEffect(() => {
    return () => {
      clearHideTimer()
    }
  }, [clearHideTimer])

  if (!isFullscreen) {
    return <>{children}</>
  }

  return (
    <div
      data-testid="theater-container"
      className="relative h-full w-full bg-black"
      onMouseMove={handleMouseMove}
    >
      {children}

      <div
        data-testid="theater-hud-wrapper"
        className={`absolute inset-0 pointer-events-none transition-opacity duration-300 ${
          isHUDVisible ? 'opacity-100' : 'opacity-0'
        }`}
      >
        {/* HUD content slots (TopHUD, BottomHUD) added by BL-200 */}
      </div>
    </div>
  )
}
