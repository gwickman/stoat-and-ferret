import { useEffect } from 'react'
import { useComposeStore } from '../stores/composeStore'
import { useTimelineStore } from '../stores/timelineStore'

export default function TimelinePage() {
  const tracks = useTimelineStore((s) => s.tracks)
  const duration = useTimelineStore((s) => s.duration)
  const timelineLoading = useTimelineStore((s) => s.isLoading)
  const timelineError = useTimelineStore((s) => s.error)

  const presets = useComposeStore((s) => s.presets)
  const presetsLoading = useComposeStore((s) => s.isLoading)
  const presetsError = useComposeStore((s) => s.error)
  const fetchPresets = useComposeStore((s) => s.fetchPresets)

  useEffect(() => {
    fetchPresets()
  }, [fetchPresets])

  const isLoading = timelineLoading || presetsLoading
  const error = timelineError || presetsError

  if (isLoading) {
    return (
      <div className="p-6" data-testid="timeline-page">
        <h2 className="mb-4 text-2xl font-semibold">Timeline</h2>
        <p className="text-gray-400" data-testid="timeline-loading">Loading...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6" data-testid="timeline-page">
        <h2 className="mb-4 text-2xl font-semibold">Timeline</h2>
        <p className="text-red-400" data-testid="timeline-error">{error}</p>
      </div>
    )
  }

  const isEmpty = tracks.length === 0 && presets.length === 0

  return (
    <div className="p-6" data-testid="timeline-page">
      <h2 className="mb-4 text-2xl font-semibold">Timeline</h2>
      {isEmpty ? (
        <p className="text-gray-400" data-testid="timeline-empty">
          No timeline data. Select a project to view its timeline.
        </p>
      ) : (
        <div data-testid="timeline-content">
          {tracks.length > 0 && (
            <div data-testid="timeline-tracks">
              <h3 className="mb-2 text-lg font-medium">
                Tracks ({tracks.length}) &middot; {duration.toFixed(1)}s
              </h3>
              <ul className="space-y-1">
                {tracks.map((track) => (
                  <li key={track.id} className="rounded bg-gray-800 px-3 py-2 text-sm">
                    {track.label} ({track.track_type}) &middot; {track.clips.length} clips
                  </li>
                ))}
              </ul>
            </div>
          )}
          {presets.length > 0 && (
            <div className="mt-4" data-testid="timeline-presets">
              <h3 className="mb-2 text-lg font-medium">Layout Presets ({presets.length})</h3>
              <ul className="space-y-1">
                {presets.map((preset) => (
                  <li key={preset.name} className="rounded bg-gray-800 px-3 py-2 text-sm">
                    {preset.name} &mdash; {preset.description}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
