import { useCallback, useEffect, useRef, useState } from 'react'

export type ConnectionState = 'connected' | 'disconnected' | 'reconnecting'

export interface WebSocketHook {
  state: ConnectionState
  send: (data: string) => void
  lastMessage: MessageEvent | null
  messages: MessageEvent[]
}

const BASE_DELAY = 1000
const MAX_DELAY = 30_000

export function useWebSocket(url: string): WebSocketHook {
  const [state, setState] = useState<ConnectionState>('disconnected')
  const [messages, setMessages] = useState<MessageEvent[]>([])
  const [tick, setTick] = useState(0)
  const queueRef = useRef<MessageEvent[]>([])
  const wsRef = useRef<WebSocket | null>(null)
  const retryCount = useRef(0)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const unmountedRef = useRef(false)

  const connect = useCallback(() => {
    if (unmountedRef.current) return

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      if (unmountedRef.current) return
      retryCount.current = 0
      setState('connected')
    }

    ws.onmessage = (event: MessageEvent) => {
      if (unmountedRef.current) return
      queueRef.current.push(event)
      setTick((n) => n + 1)
    }

    ws.onclose = () => {
      if (unmountedRef.current) return
      wsRef.current = null
      setState('reconnecting')
      const delay = Math.min(
        BASE_DELAY * 2 ** retryCount.current,
        MAX_DELAY,
      )
      retryCount.current += 1
      timerRef.current = setTimeout(connect, delay)
    }

    ws.onerror = () => {
      // onclose will fire after onerror, which handles reconnection
    }
  }, [url])

  useEffect(() => {
    unmountedRef.current = false
    connect()

    return () => {
      unmountedRef.current = true
      if (timerRef.current) clearTimeout(timerRef.current)
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.close()
      }
    }
  }, [connect])

  useEffect(() => {
    if (queueRef.current.length === 0) return
    const drained = [...queueRef.current]
    queueRef.current = []
    setMessages(drained)
  }, [tick])

  const lastMessage = messages.at(-1) ?? null

  const send = useCallback((data: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data)
    }
  }, [])

  return { state, send, lastMessage, messages }
}
