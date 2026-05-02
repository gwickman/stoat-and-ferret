import { useCallback, useRef, useEffect } from 'react'

export function useAnnounce(): { announce: (message: string, priority?: 'polite' | 'assertive') => void } {
  const regionRef = useRef<HTMLElement | null>(null)
  const assertiveRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    regionRef.current = document.getElementById('announcements')
    assertiveRef.current = document.getElementById('announcements-assertive')
    return () => {
      regionRef.current = null
      assertiveRef.current = null
    }
  }, [])

  const announce = useCallback((message: string, priority: 'polite' | 'assertive' = 'polite'): void => {
    const region = priority === 'assertive' ? assertiveRef.current : regionRef.current
    if (region) {
      region.textContent = message
    }
  }, [])

  return { announce }
}
