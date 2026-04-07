/**
 * Displays a color-coded dot indicator for render job status.
 *
 * Blue = queued, Yellow = running ("Rendering"), Green = completed,
 * Red = failed, Gray = cancelled. Unknown statuses fall back to gray.
 */

const STATUS_COLORS: Record<string, string> = {
  queued: 'bg-blue-500',
  running: 'bg-yellow-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
  cancelled: 'bg-gray-500',
}

const STATUS_LABELS: Record<string, string> = {
  queued: 'Queued',
  running: 'Rendering',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
}

const FALLBACK_COLOR = 'bg-gray-500'

interface StatusBadgeProps {
  status: string
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const color = STATUS_COLORS[status] ?? FALLBACK_COLOR
  const label = STATUS_LABELS[status] ?? status

  return (
    <span className="inline-flex items-center gap-1.5" data-testid="status-badge">
      <span
        className={`inline-block h-2.5 w-2.5 rounded-full ${color}`}
        data-testid="status-badge-dot"
      />
      <span data-testid="status-badge-label">{label}</span>
    </span>
  )
}
