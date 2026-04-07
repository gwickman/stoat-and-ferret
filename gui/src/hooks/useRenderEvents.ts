import { useEffect, useRef } from 'react'
import type { ConnectionState } from './useWebSocket'
import { useWebSocket } from './useWebSocket'
import { useRenderStore } from '../stores/renderStore'

/** All render event type strings emitted by the backend. */
const RENDER_EVENT_TYPES = new Set([
  'render_queued',
  'render_started',
  'render_progress',
  'render_completed',
  'render_failed',
  'render_cancelled',
  'render_frame_available',
  'render_queue_status',
])

function wsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws`
}

/**
 * Subscribe to render-related WebSocket events and dispatch them to the renderStore.
 *
 * Handles all 8 render event types and triggers a re-fetch on reconnection.
 */
export function useRenderEvents(): void {
  const { lastMessage, state } = useWebSocket(wsUrl())
  const prevStateRef = useRef<ConnectionState>(state)

  // Dispatch incoming WS messages to store actions
  useEffect(() => {
    if (!lastMessage) return

    let parsed: { type: string; payload: Record<string, unknown> }
    try {
      parsed = JSON.parse(lastMessage.data)
    } catch {
      return // Ignore malformed JSON
    }

    if (!parsed.type || !RENDER_EVENT_TYPES.has(parsed.type)) return

    const store = useRenderStore.getState()
    const payload = parsed.payload

    switch (parsed.type) {
      case 'render_queued':
      case 'render_started':
      case 'render_completed':
      case 'render_failed':
      case 'render_cancelled':
        store.updateJob({
          id: payload.job_id as string,
          project_id: payload.project_id as string,
          status: payload.status as string,
        })
        break

      case 'render_progress':
        store.setProgress(
          payload.job_id as string,
          payload.progress as number,
          (payload.eta_seconds as number | undefined) ?? null,
          (payload.speed_ratio as number | undefined) ?? null,
        )
        break

      case 'render_frame_available':
        // Frame events update progress on the job; frame_url is informational
        store.setProgress(payload.job_id as string, payload.progress as number)
        break

      case 'render_queue_status':
        store.setQueueStatus({
          active_count: payload.active_count as number,
          pending_count: payload.pending_count as number,
          max_concurrent: payload.max_concurrent as number,
          max_queue_depth: payload.max_queue_depth as number,
        })
        break
    }
  }, [lastMessage])

  // Re-fetch on reconnection (reconnecting → connected)
  useEffect(() => {
    const prev = prevStateRef.current
    prevStateRef.current = state

    if (prev === 'reconnecting' && state === 'connected') {
      const store = useRenderStore.getState()
      store.fetchJobs()
      store.fetchQueueStatus()
    }
  }, [state])
}
