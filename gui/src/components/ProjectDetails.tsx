import { useCallback, useEffect, useState } from 'react'
import { type Clip, type Project, fetchClips } from '../hooks/useProjects'

interface ProjectDetailsProps {
  project: Project
  onBack: () => void
  onDelete: (id: string) => void
}

function formatTimecode(frames: number, fps: number): string {
  const totalSeconds = frames / fps
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toFixed(2).padStart(5, '0')}`
}

export default function ProjectDetails({ project, onBack, onDelete }: ProjectDetailsProps) {
  const [clips, setClips] = useState<Clip[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadClips = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchClips(project.id)
      setClips(result.clips)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load clips')
    } finally {
      setLoading(false)
    }
  }, [project.id])

  useEffect(() => {
    loadClips()
  }, [loadClips])

  return (
    <div data-testid="project-details">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="rounded px-2 py-1 text-sm text-gray-400 hover:bg-gray-700 hover:text-gray-200"
            data-testid="btn-back"
          >
            &larr; Back
          </button>
          <h2 className="text-2xl font-semibold" data-testid="project-detail-name">
            {project.name}
          </h2>
        </div>
        <button
          onClick={() => onDelete(project.id)}
          className="rounded border border-red-700 px-3 py-1 text-sm text-red-400 hover:bg-red-900/30"
          data-testid="btn-delete-project"
        >
          Delete Project
        </button>
      </div>

      <div className="mb-6 space-y-1 text-sm text-gray-400" data-testid="project-metadata">
        <p>
          Resolution: {project.output_width}x{project.output_height}
        </p>
        <p>Frame Rate: {project.output_fps} fps</p>
        <p>Created: {new Date(project.created_at).toLocaleString()}</p>
      </div>

      <h3 className="mb-3 text-lg font-medium text-gray-200">
        Clips ({clips.length})
      </h3>

      {loading && (
        <div className="py-8 text-center text-gray-400" data-testid="clips-loading">
          Loading clips...
        </div>
      )}

      {error && (
        <div className="py-8 text-center text-red-400" data-testid="clips-error">
          {error}
        </div>
      )}

      {!loading && !error && clips.length === 0 && (
        <div className="py-8 text-center text-gray-400" data-testid="clips-empty">
          No clips in this project yet.
        </div>
      )}

      {!loading && !error && clips.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm" data-testid="clips-table">
            <thead>
              <tr className="border-b border-gray-700 text-gray-400">
                <th className="pb-2 pr-4">#</th>
                <th className="pb-2 pr-4">Timeline Position</th>
                <th className="pb-2 pr-4">In Point</th>
                <th className="pb-2 pr-4">Out Point</th>
                <th className="pb-2">Duration</th>
              </tr>
            </thead>
            <tbody>
              {clips.map((clip, index) => (
                <tr
                  key={clip.id}
                  className="border-b border-gray-800 text-gray-300"
                  data-testid={`clip-row-${clip.id}`}
                >
                  <td className="py-2 pr-4">{index + 1}</td>
                  <td className="py-2 pr-4" data-testid={`clip-position-${clip.id}`}>
                    {formatTimecode(clip.timeline_position, project.output_fps)}
                  </td>
                  <td className="py-2 pr-4" data-testid={`clip-in-${clip.id}`}>
                    {formatTimecode(clip.in_point, project.output_fps)}
                  </td>
                  <td className="py-2 pr-4" data-testid={`clip-out-${clip.id}`}>
                    {formatTimecode(clip.out_point, project.output_fps)}
                  </td>
                  <td className="py-2" data-testid={`clip-duration-${clip.id}`}>
                    {formatTimecode(clip.out_point - clip.in_point, project.output_fps)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
