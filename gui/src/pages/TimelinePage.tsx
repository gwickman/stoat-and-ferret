import { useEffect } from 'react'
import TimelineCanvas from '../components/TimelineCanvas'
import LayoutSelector from '../components/LayoutSelector'
import LayoutPreview from '../components/LayoutPreview'
import LayerStack from '../components/LayerStack'
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
          <div data-testid="timeline-tracks">
            <TimelineCanvas tracks={tracks} duration={duration} />
          </div>
          {presets.length > 0 && (
            <div className="mt-4" data-testid="timeline-presets">
              <h3 className="mb-2 text-lg font-medium">Layout</h3>
              <div className="grid gap-4 lg:grid-cols-3">
                <div className="lg:col-span-2 space-y-4">
                  <LayoutSelector />
                  <LayoutPreview />
                </div>
                <div>
                  <LayerStack />
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
