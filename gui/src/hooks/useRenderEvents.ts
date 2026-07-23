import { useEffect, useRef } from 'react'
import type { ConnectionState } from './useWebSocket'
import { useWebSocket } from './useWebSocket'
import { useRenderStore } from '../stores/renderStore'
import type { SetProgressOptions } from '../stores/renderStore'

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
  const { messages, state } = useWebSocket(wsUrl())
  const prevStateRef = useRef<ConnectionState>(state)

  // Dispatch incoming WS messages to store actions
  useEffect(() => {
    if (messages.length === 0) return

    const store = useRenderStore.getState()

    for (const msg of messages) {
      let parsed: { type: string; payload: Record<string, unknown> }
      try {
        parsed = JSON.parse(msg.data)
      } catch {
        continue // Ignore malformed JSON
      }

      if (!parsed.type || !RENDER_EVENT_TYPES.has(parsed.type)) continue

      const payload = parsed.payload

      switch (parsed.type) {
        case 'render_queued':
        case 'render_started':
        case 'render_failed':
        case 'render_cancelled':
          store.updateJob({
            id: payload.job_id as string,
            project_id: payload.project_id as string,
            status: payload.status as string,
          })
          break

        case 'render_completed':
          store.updateJob({
            id: payload.job_id as string,
            project_id: payload.project_id as string,
            status: payload.status as string,
            output_path: payload.output_path as string | null,
          })
          break

        case 'render_progress': {
          // BL-702: split into two groups matching the BL-659 setProgress contract.
          // Always-overwrite: etaSeconds/speedRatio use ?? null (absent means "not applicable").
          // Preserve-prior-value: frameCount/fps/encoderName/encoderType use conditional
          // assignment so absent payload fields do not clear previously-stored values.
          const progressOpts: SetProgressOptions = {
            jobId: payload.job_id as string,
            progress: payload.progress as number,
            etaSeconds: (payload.eta_seconds as number | undefined) ?? null,
            speedRatio: (payload.speed_ratio as number | undefined) ?? null,
          }
          if (payload.frame_count !== undefined) progressOpts.frameCount = payload.frame_count as number | null
          if (payload.fps !== undefined) progressOpts.fps = payload.fps as number | null
          if (payload.encoder_name !== undefined) progressOpts.encoderName = payload.encoder_name as string | null
          if (payload.encoder_type !== undefined) progressOpts.encoderType = payload.encoder_type as string | null
          store.setProgress(progressOpts)
          break
        }

        case 'render_frame_available':
          store.setProgress({
            jobId: payload.job_id as string,
            progress: payload.progress as number,
          })
          store.setFrameUrl(
            payload.job_id as string,
            (payload.frame_url as string | null) ?? null,
          )
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
    }
  }, [messages])

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
