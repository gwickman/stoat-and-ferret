import { useEffect, useState } from 'react'
import { useWebSocket } from '../../hooks/useWebSocket'

export type ProxyStatusValue = 'ready' | 'generating' | 'none'

interface ProxyStatusBadgeProps {
  videoId: string
  proxyStatus?: ProxyStatusValue
}

const STATUS_COLORS: Record<ProxyStatusValue, string> = {
  ready: 'bg-green-500',
  generating: 'bg-yellow-500',
  none: 'bg-gray-500',
}

const STATUS_LABELS: Record<ProxyStatusValue, string> = {
  ready: 'Proxy ready',
  generating: 'Proxy generating',
  none: 'No proxy',
}

function wsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}/ws`
}

/**
 * Displays a colored dot indicating proxy generation status for a video.
 *
 * Green = ready, Yellow = generating, Gray = none.
 * Subscribes to PROXY_READY WebSocket events for real-time updates.
 */
export default function ProxyStatusBadge({
  videoId,
  proxyStatus = 'none',
}: ProxyStatusBadgeProps) {
  const [status, setStatus] = useState<ProxyStatusValue>(proxyStatus)
  const { lastMessage } = useWebSocket(wsUrl())

  useEffect(() => {
    setStatus(proxyStatus)
  }, [proxyStatus])

  useEffect(() => {
    if (!lastMessage) return
    try {
      const data = JSON.parse(lastMessage.data)
      if (data.type === 'proxy.ready' && data.payload?.video_id === videoId) {
        setStatus('ready')
      }
    } catch {
      // Ignore non-JSON messages
    }
  }, [lastMessage, videoId])

  return (
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full ${STATUS_COLORS[status]}`}
      title={STATUS_LABELS[status]}
      data-testid="proxy-status-badge"
      data-status={status}
    />
  )
}
