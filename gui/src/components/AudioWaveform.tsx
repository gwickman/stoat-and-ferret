import { useState, useEffect } from 'react'

interface AudioWaveformProps {
  videoId: string
}

/** Displays waveform PNG as a background image for audio track clips. */
export default function AudioWaveform({ videoId }: AudioWaveformProps) {
  const [bgUrl, setBgUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    setBgUrl(null)
    setFailed(false)

    fetch(`/api/v1/videos/${videoId}/waveform.png`)
      .then((res) => {
        if (!res.ok) throw new Error('Not available')
        return res.blob()
      })
      .then((blob) => {
        if (!cancelled) {
          setBgUrl(URL.createObjectURL(blob))
        }
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })

    return () => {
      cancelled = true
    }
  }, [videoId])

  if (!bgUrl && !failed) return null

  return (
    <div
      data-testid="audio-waveform"
      className="pointer-events-none absolute inset-0"
      style={
        bgUrl
          ? {
              backgroundImage: `url(${bgUrl})`,
              backgroundSize: '100% 100%',
              backgroundRepeat: 'no-repeat',
              opacity: 0.6,
            }
          : {
              background: 'linear-gradient(to right, #4b5563, #6b7280, #4b5563)',
              opacity: 0.3,
            }
      }
    />
  )
}
