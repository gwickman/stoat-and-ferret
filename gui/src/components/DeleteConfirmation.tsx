import { useState } from 'react'
import { deleteProject } from '../hooks/useProjects'

interface DeleteConfirmationProps {
  open: boolean
  projectId: string
  projectName: string
  onClose: () => void
  onDeleted: () => void
}

export default function DeleteConfirmation({
  open,
  projectId,
  projectName,
  onClose,
  onDeleted,
}: DeleteConfirmationProps) {
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleConfirm = async () => {
    setDeleting(true)
    setError(null)
    try {
      await deleteProject(projectId)
      onDeleted()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete project')
    } finally {
      setDeleting(false)
    }
  }

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      data-testid="delete-confirmation"
    >
      <div className="w-full max-w-sm rounded-lg border border-gray-700 bg-gray-800 p-6">
        <h3 className="mb-2 text-lg font-semibold text-gray-200">Delete Project</h3>
        <p className="mb-4 text-sm text-gray-400">
          Are you sure you want to delete{' '}
          <span className="font-medium text-gray-200" data-testid="delete-project-name">
            {projectName}
          </span>
          ? This action cannot be undone.
        </p>

        {error && (
          <p className="mb-4 text-sm text-red-400" data-testid="delete-error">
            {error}
          </p>
        )}

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-gray-600 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700"
            data-testid="btn-cancel-delete"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={deleting}
            className="rounded bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700 disabled:opacity-50"
            data-testid="btn-confirm-delete"
          >
            {deleting ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  )
}
