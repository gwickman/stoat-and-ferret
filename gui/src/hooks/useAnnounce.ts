import { useRef, useEffect } from 'react'

export function useAnnounce(): { announce: (message: string) => void } {
  const regionRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    regionRef.current = document.getElementById('announcements')
    return () => {
      regionRef.current = null
    }
  }, [])

  const announce = (message: string): void => {
    if (regionRef.current) {
      regionRef.current.textContent = message
    }
  }

  return { announce }
}
