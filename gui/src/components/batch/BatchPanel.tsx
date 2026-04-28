import { useState } from 'react'
import { useBatchStore, type BatchJob } from '../../stores/batchStore'

interface BatchEntry {
  project_id: string
  output_path: string
  quality: string
}

const QUALITIES = ['low', 'medium', 'high'] as const

interface BatchSubmitResponse {
  batch_id: string
  jobs_queued: number
  status: string
}

interface BatchPanelProps {
  /** Called with the new batch_id after a successful submission. */
  onBatchSubmitted?: (batchId: string) => void
}

function emptyEntry(): BatchEntry {
  return { project_id: '', output_path: '', quality: 'medium' }
}

function uuid(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `tmp-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

/**
 * Form for submitting a batch of render jobs (FR-001).
 *
 * Validates that at least one row has a non-empty project_id and
 * output_path before submission. Surfaces 422 errors inline; 5xx
 * errors via a banner that preserves form state for retry.
 */
export default function BatchPanel({ onBatchSubmitted }: BatchPanelProps) {
  const submitting = useBatchStore((s) => s.submitting)
  const submitError = useBatchStore((s) => s.submitError)
  const setSubmitting = useBatchStore((s) => s.setSubmitting)
  const setSubmitError = useBatchStore((s) => s.setSubmitError)
  const addJob = useBatchStore((s) => s.addJob)

  const [entries, setEntries] = useState<BatchEntry[]>([emptyEntry()])
  const [validationError, setValidationError] = useState<string | null>(null)

  const updateEntry = (index: number, patch: Partial<BatchEntry>): void => {
    setEntries((prev) => {
      const next = [...prev]
      next[index] = { ...next[index], ...patch }
      return next
    })
    if (validationError) setValidationError(null)
  }

  const addRow = (): void => setEntries((prev) => [...prev, emptyEntry()])
  const removeRow = (index: number): void =>
    setEntries((prev) => (prev.length === 1 ? prev : prev.filter((_, i) => i !== index)))

  const handleSubmit = async (event: React.FormEvent): Promise<void> => {
    event.preventDefault()
    setSubmitError(null)
    setValidationError(null)

    const validEntries = entries.filter(
      (e) => e.project_id.trim() !== '' && e.output_path.trim() !== '',
    )
    if (validEntries.length === 0) {
      setValidationError('Add at least one job with project ID and output path.')
      return
    }

    setSubmitting(true)
    try {
      const res = await fetch('/api/v1/render/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jobs: validEntries }),
      })
      if (!res.ok) {
        const body: unknown = await res.json().catch(() => null)
        const detail =
          (body as { detail?: { message?: string } } | null)?.detail?.message ??
          (typeof (body as { detail?: unknown } | null)?.detail === 'string'
            ? ((body as { detail: string }).detail)
            : null) ??
          `Server error (${res.status})`
        setSubmitError(detail)
        return
      }
      const json = (await res.json()) as BatchSubmitResponse
      const submittedAt = Date.now()
      // Seed the store with placeholder jobs so the list renders
      // immediately; the polling hook will replace fields as they
      // come in from the server.
      for (const entry of validEntries) {
        const seed: BatchJob = {
          job_id: uuid(),
          batch_id: json.batch_id,
          project_id: entry.project_id,
          status: 'queued',
          progress: 0,
          error: null,
          submitted_at: submittedAt,
        }
        addJob(seed)
      }
      setEntries([emptyEntry()])
      onBatchSubmitted?.(json.batch_id)
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to submit batch')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section
      data-testid="batch-panel"
      aria-label="Batch render submission"
      className="rounded border border-gray-700 bg-gray-800 p-4"
    >
      <h3 className="mb-3 text-lg font-medium text-gray-200">Submit Batch Render</h3>

      <form onSubmit={handleSubmit} className="space-y-3">
        {entries.map((entry, idx) => (
          <div
            key={idx}
            data-testid={`batch-entry-${idx}`}
            className="grid grid-cols-12 gap-2 rounded border border-gray-700 bg-gray-900 p-3"
          >
            <div className="col-span-4">
              <label htmlFor={`batch-project-${idx}`} className="block text-xs text-gray-400">
                Project ID
              </label>
              <input
                id={`batch-project-${idx}`}
                data-testid={`batch-project-${idx}`}
                value={entry.project_id}
                onChange={(e) => updateEntry(idx, { project_id: e.target.value })}
                className="w-full rounded bg-gray-800 px-2 py-1 text-sm text-gray-100"
                disabled={submitting}
              />
            </div>
            <div className="col-span-5">
              <label htmlFor={`batch-output-${idx}`} className="block text-xs text-gray-400">
                Output Path
              </label>
              <input
                id={`batch-output-${idx}`}
                data-testid={`batch-output-${idx}`}
                value={entry.output_path}
                onChange={(e) => updateEntry(idx, { output_path: e.target.value })}
                className="w-full rounded bg-gray-800 px-2 py-1 text-sm text-gray-100"
                disabled={submitting}
              />
            </div>
            <div className="col-span-2">
              <label htmlFor={`batch-quality-${idx}`} className="block text-xs text-gray-400">
                Quality
              </label>
              <select
                id={`batch-quality-${idx}`}
                data-testid={`batch-quality-${idx}`}
                value={entry.quality}
                onChange={(e) => updateEntry(idx, { quality: e.target.value })}
                className="w-full rounded bg-gray-800 px-2 py-1 text-sm text-gray-100"
                disabled={submitting}
              >
                {QUALITIES.map((q) => (
                  <option key={q} value={q}>
                    {q}
                  </option>
                ))}
              </select>
            </div>
            <div className="col-span-1 flex items-end">
              <button
                type="button"
                data-testid={`batch-remove-${idx}`}
                onClick={() => removeRow(idx)}
                disabled={submitting || entries.length === 1}
                className="rounded bg-gray-700 px-2 py-1 text-xs text-gray-200 hover:bg-gray-600 disabled:cursor-not-allowed disabled:opacity-40"
                aria-label={`Remove job ${idx + 1}`}
              >
                ×
              </button>
            </div>
          </div>
        ))}

        {validationError && (
          <p data-testid="batch-validation-error" className="text-sm text-red-400">
            {validationError}
          </p>
        )}

        {submitError && (
          <p data-testid="batch-submit-error" className="text-sm text-red-400" role="alert">
            {submitError}
          </p>
        )}

        <div className="flex items-center justify-between">
          <button
            type="button"
            data-testid="batch-add-row"
            onClick={addRow}
            disabled={submitting}
            className="rounded bg-gray-700 px-3 py-1 text-sm text-gray-200 hover:bg-gray-600 disabled:opacity-50"
          >
            + Add Job
          </button>
          <button
            type="submit"
            data-testid="batch-submit"
            disabled={submitting}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? 'Submitting…' : 'Submit Batch'}
          </button>
        </div>
      </form>
    </section>
  )
}
