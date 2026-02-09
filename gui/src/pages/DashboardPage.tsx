import ActivityLog from '../components/ActivityLog'
import HealthCards from '../components/HealthCards'
import MetricsCards from '../components/MetricsCards'
import { useHealth } from '../hooks/useHealth'
import { useMetrics } from '../hooks/useMetrics'
import { useWebSocket } from '../hooks/useWebSocket'

const REFRESH_INTERVAL = 30_000

function wsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws`
}

export default function DashboardPage() {
  const health = useHealth(REFRESH_INTERVAL)
  const metrics = useMetrics(REFRESH_INTERVAL)
  const { lastMessage } = useWebSocket(wsUrl())

  return (
    <div className="space-y-6 p-6">
      <h2 className="text-2xl font-semibold">Dashboard</h2>
      <HealthCards health={health} />
      <MetricsCards metrics={metrics} />
      <ActivityLog lastMessage={lastMessage} />
    </div>
  )
}
