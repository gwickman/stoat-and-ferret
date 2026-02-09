import { useHealth, type HealthStatus } from '../hooks/useHealth'

const STATUS_COLORS: Record<HealthStatus, string> = {
  healthy: 'bg-green-500',
  degraded: 'bg-yellow-500',
  unhealthy: 'bg-red-500',
}

const STATUS_LABELS: Record<HealthStatus, string> = {
  healthy: 'Healthy',
  degraded: 'Degraded',
  unhealthy: 'Unhealthy',
}

export default function HealthIndicator() {
  const { status } = useHealth()

  return (
    <div className="flex items-center gap-2" data-testid="health-indicator">
      <span
        className={`inline-block h-3 w-3 rounded-full ${STATUS_COLORS[status]}`}
        data-testid="health-dot"
        data-status={status}
      />
      <span className="text-sm text-gray-300">{STATUS_LABELS[status]}</span>
    </div>
  )
}
