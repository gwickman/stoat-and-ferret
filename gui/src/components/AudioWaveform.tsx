import { useState, useEffect } from 'react'

interface AudioWaveformProps {
  readonly videoId: string
}

/** Displays waveform PNG as a background image for audio track clips. */
export default function AudioWaveform({ videoId }: Readonly<AudioWaveformProps>) {
  const [bgUrl, setBgUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    // eslint-disable-next-line react-hooks/set-state-in-effect -- Intentional reset-before-fetch: clears prior URL/error state synchronously when videoId changes before the async load begins.
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
