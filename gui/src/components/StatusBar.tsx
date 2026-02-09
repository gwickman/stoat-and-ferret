import type { ConnectionState } from '../hooks/useWebSocket'

const STATE_LABELS: Record<ConnectionState, string> = {
  connected: 'Connected',
  disconnected: 'Disconnected',
  reconnecting: 'Reconnecting...',
}

const STATE_COLORS: Record<ConnectionState, string> = {
  connected: 'text-green-400',
  disconnected: 'text-red-400',
  reconnecting: 'text-yellow-400',
}

interface StatusBarProps {
  connectionState: ConnectionState
}

export default function StatusBar({ connectionState }: StatusBarProps) {
  return (
    <footer
      className="flex items-center justify-between border-t border-gray-700 bg-gray-900 px-4 py-2 text-sm"
      data-testid="status-bar"
    >
      <span className={STATE_COLORS[connectionState]}>
        WebSocket: {STATE_LABELS[connectionState]}
      </span>
    </footer>
  )
}
