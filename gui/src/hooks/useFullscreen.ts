import { useCallback, useEffect } from 'react'
import { useTheaterStore } from '../stores/theaterStore'

/**
 * Hook wrapping the Fullscreen API with fullscreenchange event listener.
 * Derives fullscreen state from the browser event, not click state (NFR-002).
 */
export function useFullscreen(containerRef: React.RefObject<HTMLElement | null>) {
  const enterTheater = useTheaterStore((s) => s.enterTheater)
  const exitTheater = useTheaterStore((s) => s.exitTheater)

  useEffect(() => {
    function handleFullscreenChange() {
      if (document.fullscreenElement) {
        enterTheater()
      } else {
        exitTheater()
      }
    }

    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
    }
  }, [enterTheater, exitTheater])

  const enter = useCallback(async () => {
    const el = containerRef.current
    if (el && !document.fullscreenElement) {
      await el.requestFullscreen()
    }
  }, [containerRef])

  const exit = useCallback(async () => {
    if (document.fullscreenElement) {
      await document.exitFullscreen()
    }
  }, [])

  return { enter, exit }
}
