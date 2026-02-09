import type { HealthState } from '../hooks/useHealth'

interface HealthCardProps {
  name: string
  status: string
}

const STATUS_COLORS: Record<string, string> = {
  ok: 'bg-green-900/50 border-green-700',
  error: 'bg-red-900/50 border-red-700',
}

const DOT_COLORS: Record<string, string> = {
  ok: 'bg-green-500',
  error: 'bg-red-500',
}

const STATUS_LABELS: Record<string, string> = {
  ok: 'Operational',
  error: 'Error',
}

function HealthCard({ name, status }: HealthCardProps) {
  const colors = STATUS_COLORS[status] ?? 'bg-yellow-900/50 border-yellow-700'
  const dot = DOT_COLORS[status] ?? 'bg-yellow-500'
  const label = STATUS_LABELS[status] ?? 'Unknown'

  return (
    <div
      className={`rounded border p-4 ${colors}`}
      data-testid={`health-card-${name}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-200">{name}</span>
        <span
          className={`inline-block h-2.5 w-2.5 rounded-full ${dot}`}
          data-testid={`health-dot-${name}`}
          data-status={status}
        />
      </div>
      <p className="mt-1 text-xs text-gray-400">{label}</p>
    </div>
  )
}

/** Expected components from the /health/ready endpoint. */
const COMPONENTS: Record<string, string> = {
  database: 'Python API',
  ffmpeg: 'FFmpeg',
}

interface HealthCardsProps {
  health: HealthState
}

export default function HealthCards({ health }: HealthCardsProps) {
  return (
    <div data-testid="health-cards">
      <h3 className="mb-3 text-lg font-semibold">System Health</h3>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {Object.entries(COMPONENTS).map(([key, label]) => {
          const check = health.checks[key]
          return (
            <HealthCard
              key={key}
              name={label}
              status={check?.status ?? 'unknown'}
            />
          )
        })}
        <HealthCard
          name="Rust Core"
          status={health.status === 'unhealthy' ? 'error' : 'ok'}
        />
      </div>
    </div>
  )
}
