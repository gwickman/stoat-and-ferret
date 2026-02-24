import { useCallback, useEffect, useState } from 'react'
import { type Clip } from '../hooks/useProjects'
import { useVideos } from '../hooks/useVideos'
import { useClipStore } from '../stores/clipStore'

interface ClipFormModalProps {
  mode: 'add' | 'edit'
  clip?: Clip
  projectId: string
  onClose: () => void
  onSaved: () => void
}

export default function ClipFormModal({
  mode,
  clip,
  projectId,
  onClose,
  onSaved,
}: ClipFormModalProps) {
  const [sourceVideoId, setSourceVideoId] = useState(clip?.source_video_id ?? '')
  const [inPoint, setInPoint] = useState(clip?.in_point?.toString() ?? '')
  const [outPoint, setOutPoint] = useState(clip?.out_point?.toString() ?? '')
  const [timelinePosition, setTimelinePosition] = useState(
    clip?.timeline_position?.toString() ?? '',
  )
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const { videos, loading: videosLoading } = useVideos({
    searchQuery: '',
    sortField: 'name',
    sortOrder: 'asc',
    page: 0,
    pageSize: 1000,
  })

  const createClip = useClipStore((s) => s.createClip)
  const updateClip = useClipStore((s) => s.updateClip)

  // Set default source video when videos load and no video selected
  useEffect(() => {
    if (mode === 'add' && !sourceVideoId && videos.length > 0) {
      setSourceVideoId(videos[0].id)
    }
  }, [mode, sourceVideoId, videos])

  const validate = useCallback((): string | null => {
    if (!sourceVideoId && mode === 'add') return 'Source video is required'
    if (!inPoint.trim()) return 'In point is required'
    if (!outPoint.trim()) return 'Out point is required'
    if (!timelinePosition.trim()) return 'Timeline position is required'
    const inVal = parseInt(inPoint, 10)
    const outVal = parseInt(outPoint, 10)
    const posVal = parseInt(timelinePosition, 10)
    if (isNaN(inVal) || inVal < 0) return 'In point must be a non-negative number'
    if (isNaN(outVal) || outVal < 0) return 'Out point must be a non-negative number'
    if (isNaN(posVal) || posVal < 0) return 'Timeline position must be a non-negative number'
    if (outVal <= inVal) return 'Out point must be greater than in point'
    return null
  }, [sourceVideoId, inPoint, outPoint, timelinePosition, mode])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const validationError = validate()
    if (validationError) {
      setError(validationError)
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      if (mode === 'add') {
        await createClip(projectId, {
          source_video_id: sourceVideoId,
          in_point: parseInt(inPoint, 10),
          out_point: parseInt(outPoint, 10),
          timeline_position: parseInt(timelinePosition, 10),
        })
      } else if (clip) {
        await updateClip(projectId, clip.id, {
          in_point: parseInt(inPoint, 10),
          out_point: parseInt(outPoint, 10),
          timeline_position: parseInt(timelinePosition, 10),
        })
      }
      onSaved()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Operation failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      data-testid="clip-form-modal"
    >
      <div className="w-full max-w-md rounded-lg border border-gray-700 bg-gray-800 p-6">
        <h3 className="mb-4 text-lg font-semibold text-gray-200">
          {mode === 'add' ? 'Add Clip' : 'Edit Clip'}
        </h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'add' && (
            <div>
              <label htmlFor="source-video" className="mb-1 block text-sm text-gray-400">
                Source Video
              </label>
              <select
                id="source-video"
                value={sourceVideoId}
                onChange={(e) => setSourceVideoId(e.target.value)}
                className="w-full rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-white"
                data-testid="select-source-video"
                disabled={videosLoading}
              >
                {videosLoading && <option value="">Loading videos...</option>}
                {!videosLoading && videos.length === 0 && (
                  <option value="">No videos available</option>
                )}
                {videos.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.filename}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label htmlFor="in-point" className="mb-1 block text-sm text-gray-400">
              In Point (frames)
            </label>
            <input
              id="in-point"
              type="number"
              min={0}
              value={inPoint}
              onChange={(e) => setInPoint(e.target.value)}
              className="w-full rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none"
              placeholder="0"
              data-testid="input-in-point"
            />
          </div>

          <div>
            <label htmlFor="out-point" className="mb-1 block text-sm text-gray-400">
              Out Point (frames)
            </label>
            <input
              id="out-point"
              type="number"
              min={0}
              value={outPoint}
              onChange={(e) => setOutPoint(e.target.value)}
              className="w-full rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none"
              placeholder="100"
              data-testid="input-out-point"
            />
          </div>

          <div>
            <label htmlFor="timeline-position" className="mb-1 block text-sm text-gray-400">
              Timeline Position (frames)
            </label>
            <input
              id="timeline-position"
              type="number"
              min={0}
              value={timelinePosition}
              onChange={(e) => setTimelinePosition(e.target.value)}
              className="w-full rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none"
              placeholder="0"
              data-testid="input-timeline-position"
            />
          </div>

          {error && (
            <p className="text-sm text-red-400" data-testid="clip-form-error">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded border border-gray-600 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700"
              data-testid="btn-clip-cancel"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
              data-testid="btn-clip-save"
            >
              {isSubmitting ? 'Saving...' : mode === 'add' ? 'Add Clip' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
