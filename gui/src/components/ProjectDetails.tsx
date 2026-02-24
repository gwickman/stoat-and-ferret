import { useCallback, useEffect, useState } from 'react'
import { type Clip, type Project, fetchClips } from '../hooks/useProjects'
import { useClipStore } from '../stores/clipStore'
import ClipFormModal from './ClipFormModal'

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

  // Clip form modal state
  const [showClipForm, setShowClipForm] = useState(false)
  const [editingClip, setEditingClip] = useState<Clip | undefined>(undefined)

  // Delete clip confirmation state
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deletingClip, setDeletingClip] = useState<Clip | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  const clipStoreIsLoading = useClipStore((s) => s.isLoading)
  const clipStoreDeleteClip = useClipStore((s) => s.deleteClip)

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

  const handleAddClip = () => {
    setEditingClip(undefined)
    setShowClipForm(true)
  }

  const handleEditClip = (clip: Clip) => {
    setEditingClip(clip)
    setShowClipForm(true)
  }

  const handleClipSaved = () => {
    loadClips()
  }

  const handleDeleteClipClick = (clip: Clip) => {
    setDeletingClip(clip)
    setDeleteError(null)
    setShowDeleteConfirm(true)
  }

  const handleConfirmDelete = async () => {
    if (!deletingClip) return
    setIsDeleting(true)
    setDeleteError(null)
    try {
      await clipStoreDeleteClip(project.id, deletingClip.id)
      setShowDeleteConfirm(false)
      setDeletingClip(null)
      loadClips()
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : 'Failed to delete clip')
    } finally {
      setIsDeleting(false)
    }
  }

  const handleCancelDelete = () => {
    setShowDeleteConfirm(false)
    setDeletingClip(null)
    setDeleteError(null)
  }

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

      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-200">
          Clips ({clips.length})
        </h3>
        <button
          onClick={handleAddClip}
          disabled={clipStoreIsLoading}
          className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          data-testid="btn-add-clip"
        >
          Add Clip
        </button>
      </div>

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
                <th className="pb-2 pr-4">Duration</th>
                <th className="pb-2">Actions</th>
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
                  <td className="py-2 pr-4" data-testid={`clip-duration-${clip.id}`}>
                    {formatTimecode(clip.out_point - clip.in_point, project.output_fps)}
                  </td>
                  <td className="py-2">
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleEditClip(clip)}
                        disabled={clipStoreIsLoading}
                        className="rounded border border-gray-600 px-2 py-1 text-xs text-gray-300 hover:bg-gray-700 disabled:opacity-50"
                        data-testid={`btn-edit-clip-${clip.id}`}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteClipClick(clip)}
                        disabled={clipStoreIsLoading}
                        className="rounded border border-red-700 px-2 py-1 text-xs text-red-400 hover:bg-red-900/30 disabled:opacity-50"
                        data-testid={`btn-delete-clip-${clip.id}`}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showClipForm && (
        <ClipFormModal
          mode={editingClip ? 'edit' : 'add'}
          clip={editingClip}
          projectId={project.id}
          onClose={() => setShowClipForm(false)}
          onSaved={handleClipSaved}
        />
      )}

      {showDeleteConfirm && deletingClip && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          data-testid="delete-clip-confirmation"
        >
          <div className="w-full max-w-sm rounded-lg border border-gray-700 bg-gray-800 p-6">
            <h3 className="mb-2 text-lg font-semibold text-gray-200">Delete Clip</h3>
            <p className="mb-4 text-sm text-gray-400">
              Are you sure you want to delete this clip? This action cannot be undone.
            </p>

            {deleteError && (
              <p className="mb-4 text-sm text-red-400" data-testid="delete-clip-error">
                {deleteError}
              </p>
            )}

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={handleCancelDelete}
                className="rounded border border-gray-600 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700"
                data-testid="btn-cancel-delete-clip"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmDelete}
                disabled={isDeleting}
                className="rounded bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700 disabled:opacity-50"
                data-testid="btn-confirm-delete-clip"
              >
                {isDeleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
