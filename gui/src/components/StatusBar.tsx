import React from 'react'
import type { ConnectionState } from '../hooks/useWebSocket'

const FALLBACK_SOURCE_URL = 'https://github.com/gwickman/stoat-and-ferret'

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
  const linkRef = React.useRef<HTMLAnchorElement>(null)

  React.useEffect(() => {
    fetch('/api/v1/source')
      .then((r) => r.json())
      .then((d: { source_url: string }) => {
        if (linkRef.current) linkRef.current.setAttribute('href', d.source_url)
      })
      .catch(() => {
        // fallback href remains as set in JSX
      })
  }, [])

  return (
    <footer
      className="flex items-center justify-between border-t border-gray-700 bg-gray-900 px-4 py-2 text-sm"
      data-testid="status-bar"
    >
      <span className={STATE_COLORS[connectionState]}>
        WebSocket: {STATE_LABELS[connectionState]}
      </span>
      <a
        ref={linkRef}
        href={FALLBACK_SOURCE_URL}
        target="_blank"
        rel="noreferrer"
        data-testid="source-code-link"
        className="text-xs text-muted-foreground hover:underline"
      >
        Source
      </a>
    </footer>
  )
}
