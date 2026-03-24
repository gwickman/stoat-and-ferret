import { useEffect, useState } from 'react'
import { useWebSocket } from './useWebSocket'

type JobProgressStatus =
  | 'pending'
  | 'running'
  | 'complete'
  | 'failed'
  | 'timeout'
  | 'cancelled'

interface JobProgressState {
  progress: number | null
  status: JobProgressStatus | null
  error: string | null
}

interface JobProgressEvent {
  type: string
  payload: {
    job_id: string
    progress: number
    status: JobProgressStatus
    error?: string
  }
}

function wsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws`
}

/**
 * Subscribe to real-time job progress via WebSocket.
 *
 * Wraps useWebSocket and filters for JOB_PROGRESS events matching the given jobId.
 */
export function useJobProgress(jobId: string | null): JobProgressState {
  const { lastMessage } = useWebSocket(wsUrl())
  const [state, setState] = useState<JobProgressState>({
    progress: null,
    status: null,
    error: null,
  })

  useEffect(() => {
    if (!lastMessage || !jobId) return

    try {
      const event: JobProgressEvent = JSON.parse(lastMessage.data)
      if (event.type !== 'job_progress') return
      if (event.payload.job_id !== jobId) return

      setState({
        progress: event.payload.progress,
        status: event.payload.status,
        error: event.payload.error ?? null,
      })
    } catch {
      // Ignore non-JSON messages
    }
  }, [lastMessage, jobId])

  // Reset state when jobId changes
  useEffect(() => {
    setState({ progress: null, status: null, error: null })
  }, [jobId])

  return state
}
