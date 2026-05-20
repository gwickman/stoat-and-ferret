import { useCallback, useRef, useState } from 'react'
import type { TimelineResponse } from '../generated/types'

export interface UseRenderModalResult {
  timelineLoading: boolean
  timeline: TimelineResponse | null
  timelineError: string | null
  fetchTimeline: (projectId: string) => void
  resetTimeline: () => void
  renderPlanJson: string | null
}

export function useRenderModal(): UseRenderModalResult {
  const [timelineLoading, setTimelineLoading] = useState(false)
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null)
  const [timelineError, setTimelineError] = useState<string | null>(null)

  const abortRef = useRef<AbortController | null>(null)

  const fetchTimeline = useCallback((projectId: string) => {
    if (abortRef.current) {
      abortRef.current.abort()
    }
    const controller = new AbortController()
    abortRef.current = controller

    setTimelineLoading(true)
    setTimeline(null)
    setTimelineError(null)

    async function doFetch() {
      try {
        const res = await fetch(`/api/v1/projects/${projectId}/timeline`, {
          signal: controller.signal,
        })
        if (!res.ok) {
          const body = await res.json().catch(() => null)
          const rawDetail = body?.detail
          const msg =
            typeof rawDetail === 'string'
              ? rawDetail
              : rawDetail?.message ?? `Failed to fetch timeline (${res.status})`
          setTimelineError(typeof msg === 'string' ? msg : `Failed to fetch timeline (${res.status})`)
          setTimelineLoading(false)
          return
        }
        const data: TimelineResponse = await res.json()
        if (data.duration === null || data.duration === undefined) {
          setTimelineError('Timeline duration not available')
          setTimelineLoading(false)
          return
        }
        if (data.duration <= 0) {
          setTimelineError('Timeline is empty')
          setTimelineLoading(false)
          return
        }
        setTimeline(data)
        setTimelineLoading(false)
      } catch (err) {
        if ((err as { name?: string }).name === 'AbortError') {
          return
        }
        setTimelineError('Failed to fetch timeline')
        setTimelineLoading(false)
      }
    }

    void doFetch()
  }, [])

  const resetTimeline = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
    }
    setTimelineLoading(false)
    setTimeline(null)
    setTimelineError(null)
  }, [])

  const renderPlanJson =
    timeline !== null && timeline.duration > 0
      ? JSON.stringify({ total_duration: timeline.duration })
      : null

  return { timelineLoading, timeline, timelineError, fetchTimeline, resetTimeline, renderPlanJson }
}
