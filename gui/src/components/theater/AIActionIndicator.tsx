import { useEffect, useState } from 'react'
import { useWebSocket } from '../../hooks/useWebSocket'

interface AIActionEvent {
  type: string
  payload: {
    description: string
  }
}

function wsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws`
}

/**
 * Displays the latest AI action description from WebSocket AI_ACTION events.
 *
 * Gracefully handles missing WebSocket connections by showing nothing
 * when disconnected (NFR-001 / LRN-139).
 */
export default function AIActionIndicator() {
  const { lastMessage, state } = useWebSocket(wsUrl())
  const [actionText, setActionText] = useState<string | null>(null)

  useEffect(() => {
    if (!lastMessage) return

    try {
      const event: AIActionEvent = JSON.parse(lastMessage.data)
      if (event.type !== 'ai_action') return
      setActionText(event.payload.description)
    } catch {
      // Ignore non-JSON messages (NFR-001)
    }
  }, [lastMessage])

  if (state === 'disconnected' || !actionText) {
    return null
  }

  return (
    <span
      data-testid="ai-action-indicator"
      className="truncate text-sm text-blue-300"
    >
      {actionText}
    </span>
  )
}
