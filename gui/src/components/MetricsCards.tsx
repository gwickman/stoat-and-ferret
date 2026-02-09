import type { Metrics } from '../hooks/useMetrics'

interface MetricsCardsProps {
  metrics: Metrics
}

export default function MetricsCards({ metrics }: MetricsCardsProps) {
  return (
    <div data-testid="metrics-cards">
      <h3 className="mb-3 text-lg font-semibold">Metrics</h3>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div
          className="rounded border border-gray-700 bg-gray-900 p-4"
          data-testid="metric-request-count"
        >
          <p className="text-sm text-gray-400">Total Requests</p>
          <p className="mt-1 text-2xl font-bold text-gray-100">
            {metrics.requestCount}
          </p>
        </div>
        <div
          className="rounded border border-gray-700 bg-gray-900 p-4"
          data-testid="metric-avg-duration"
        >
          <p className="text-sm text-gray-400">Avg Response Time</p>
          <p className="mt-1 text-2xl font-bold text-gray-100">
            {metrics.avgDurationMs !== null
              ? `${metrics.avgDurationMs.toFixed(1)} ms`
              : '--'}
          </p>
        </div>
      </div>
    </div>
  )
}
