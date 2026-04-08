import { useEffect, useState } from 'react'
import TimelineCanvas from '../components/TimelineCanvas'
import LayoutSelector from '../components/LayoutSelector'
import LayoutPreview from '../components/LayoutPreview'
import LayerStack from '../components/LayerStack'
import StartRenderModal from '../components/render/StartRenderModal'
import { useProjects } from '../hooks/useProjects'
import { useComposeStore } from '../stores/composeStore'
import { useProjectStore } from '../stores/projectStore'
import { useTimelineStore } from '../stores/timelineStore'

export default function TimelinePage() {
  const { projects } = useProjects()
  const selectedProjectId = useProjectStore((s) => s.selectedProjectId)
  const setSelectedProjectId = useProjectStore((s) => s.setSelectedProjectId)
  const [startModalOpen, setStartModalOpen] = useState(false)

  const tracks = useTimelineStore((s) => s.tracks)
  const duration = useTimelineStore((s) => s.duration)
  const timelineLoading = useTimelineStore((s) => s.isLoading)
  const timelineError = useTimelineStore((s) => s.error)
  const fetchTimeline = useTimelineStore((s) => s.fetchTimeline)

  const presets = useComposeStore((s) => s.presets)
  const presetsLoading = useComposeStore((s) => s.isLoading)
  const presetsError = useComposeStore((s) => s.error)
  const fetchPresets = useComposeStore((s) => s.fetchPresets)

  // Auto-select first project if none selected
  useEffect(() => {
    if (projects && projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id)
    }
  }, [projects, selectedProjectId, setSelectedProjectId])

  // Fetch timeline when project changes
  useEffect(() => {
    if (selectedProjectId) {
      fetchTimeline(selectedProjectId)
    }
  }, [selectedProjectId, fetchTimeline])

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

  console.debug('[TimelinePage] render', {
    trackCount: tracks.length,
    duration,
    presetsCount: presets.length,
    isEmpty,
    isLoading,
    error,
  })

  return (
    <div className="p-6" data-testid="timeline-page">
      <div className="mb-4 flex items-center gap-4">
        <h2 className="text-2xl font-semibold">Timeline</h2>
        <button
          onClick={() => setStartModalOpen(true)}
          disabled={!selectedProjectId}
          title={!selectedProjectId ? 'Select a project first' : undefined}
          className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Start Render
        </button>
      </div>
      <StartRenderModal
        open={startModalOpen}
        onClose={() => setStartModalOpen(false)}
        onSubmitted={() => {}}
      />
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
