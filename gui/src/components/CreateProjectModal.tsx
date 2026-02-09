import { useCallback, useState } from 'react'
import { createProject } from '../hooks/useProjects'

interface CreateProjectModalProps {
  open: boolean
  onClose: () => void
  onCreated: () => void
}

interface FormErrors {
  name?: string
  resolution?: string
  fps?: string
}

function parseResolution(value: string): { width: number; height: number } | null {
  const match = value.trim().match(/^(\d+)\s*[xX×]\s*(\d+)$/)
  if (!match) return null
  const width = parseInt(match[1], 10)
  const height = parseInt(match[2], 10)
  if (width < 1 || height < 1) return null
  return { width, height }
}

function validateForm(name: string, resolution: string, fps: string): FormErrors {
  const errors: FormErrors = {}
  if (!name.trim()) {
    errors.name = 'Project name is required'
  }
  if (!parseResolution(resolution)) {
    errors.resolution = 'Enter a valid resolution (e.g., 1920x1080)'
  }
  const fpsNum = parseInt(fps, 10)
  if (isNaN(fpsNum) || fpsNum < 1 || fpsNum > 120) {
    errors.fps = 'FPS must be between 1 and 120'
  }
  return errors
}

export default function CreateProjectModal({
  open,
  onClose,
  onCreated,
}: CreateProjectModalProps) {
  const [name, setName] = useState('')
  const [resolution, setResolution] = useState('1920x1080')
  const [fps, setFps] = useState('30')
  const [errors, setErrors] = useState<FormErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const resetForm = useCallback(() => {
    setName('')
    setResolution('1920x1080')
    setFps('30')
    setErrors({})
    setSubmitting(false)
    setSubmitError(null)
  }, [])

  const handleClose = useCallback(() => {
    resetForm()
    onClose()
  }, [resetForm, onClose])

  const handleNameChange = (value: string) => {
    setName(value)
    if (errors.name) {
      const updated = { ...errors }
      if (value.trim()) delete updated.name
      setErrors(updated)
    }
  }

  const handleResolutionChange = (value: string) => {
    setResolution(value)
    if (errors.resolution) {
      const updated = { ...errors }
      if (parseResolution(value)) delete updated.resolution
      setErrors(updated)
    }
  }

  const handleFpsChange = (value: string) => {
    setFps(value)
    if (errors.fps) {
      const updated = { ...errors }
      const fpsNum = parseInt(value, 10)
      if (!isNaN(fpsNum) && fpsNum >= 1 && fpsNum <= 120) delete updated.fps
      setErrors(updated)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const formErrors = validateForm(name, resolution, fps)
    setErrors(formErrors)
    if (Object.keys(formErrors).length > 0) return

    const res = parseResolution(resolution)!
    setSubmitting(true)
    setSubmitError(null)

    try {
      await createProject({
        name: name.trim(),
        output_width: res.width,
        output_height: res.height,
        output_fps: parseInt(fps, 10),
      })
      resetForm()
      onCreated()
      onClose()
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to create project')
    } finally {
      setSubmitting(false)
    }
  }

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      data-testid="create-project-modal"
    >
      <div className="w-full max-w-md rounded-lg border border-gray-700 bg-gray-800 p-6">
        <h3 className="mb-4 text-lg font-semibold text-gray-200">New Project</h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="project-name" className="mb-1 block text-sm text-gray-400">
              Project Name
            </label>
            <input
              id="project-name"
              type="text"
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              className="w-full rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none"
              placeholder="My Project"
              data-testid="input-project-name"
            />
            {errors.name && (
              <p className="mt-1 text-xs text-red-400" data-testid="error-name">
                {errors.name}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="project-resolution" className="mb-1 block text-sm text-gray-400">
              Resolution
            </label>
            <input
              id="project-resolution"
              type="text"
              value={resolution}
              onChange={(e) => handleResolutionChange(e.target.value)}
              className="w-full rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none"
              placeholder="1920x1080"
              data-testid="input-resolution"
            />
            {errors.resolution && (
              <p className="mt-1 text-xs text-red-400" data-testid="error-resolution">
                {errors.resolution}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="project-fps" className="mb-1 block text-sm text-gray-400">
              Frame Rate (FPS)
            </label>
            <input
              id="project-fps"
              type="number"
              value={fps}
              onChange={(e) => handleFpsChange(e.target.value)}
              min={1}
              max={120}
              className="w-full rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none"
              data-testid="input-fps"
            />
            {errors.fps && (
              <p className="mt-1 text-xs text-red-400" data-testid="error-fps">
                {errors.fps}
              </p>
            )}
          </div>

          {submitError && (
            <p className="text-sm text-red-400" data-testid="submit-error">
              {submitError}
            </p>
          )}

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={handleClose}
              className="rounded border border-gray-600 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700"
              data-testid="btn-cancel"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
              data-testid="btn-create"
            >
              {submitting ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
