import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useRenderModal } from '../useRenderModal'

beforeEach(() => {
  vi.restoreAllMocks()
})

const TIMELINE_RESPONSE = {
  project_id: 'proj-1',
  tracks: [],
  duration: 120.5,
  version: 1,
}

describe('useRenderModal', () => {
  it('starts with idle state', () => {
    const { result } = renderHook(() => useRenderModal())
    expect(result.current.timelineLoading).toBe(false)
    expect(result.current.timeline).toBeNull()
    expect(result.current.timelineError).toBeNull()
    expect(result.current.renderPlanJson).toBeNull()
  })

  it('fetchTimeline calls GET /api/v1/{projectId}/timeline', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(TIMELINE_RESPONSE), { status: 200 }),
    )

    const { result } = renderHook(() => useRenderModal())
    act(() => {
      result.current.fetchTimeline('proj-1')
    })

    await waitFor(() => {
      expect(result.current.timelineLoading).toBe(false)
    })

    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/v1/projects/proj-1/timeline',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
  })

  it('fetchTimeline constructs render_plan with timeline.duration', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(TIMELINE_RESPONSE), { status: 200 }),
    )

    const { result } = renderHook(() => useRenderModal())
    act(() => {
      result.current.fetchTimeline('proj-1')
    })

    await waitFor(() => {
      expect(result.current.timeline).not.toBeNull()
    })

    expect(result.current.renderPlanJson).toBe(JSON.stringify({ total_duration: 120.5 }))
    expect(result.current.timelineError).toBeNull()
  })

  it('fetchTimeline handles 404 error', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Not found' }), { status: 404 }),
    )

    const { result } = renderHook(() => useRenderModal())
    act(() => {
      result.current.fetchTimeline('proj-1')
    })

    await waitFor(() => {
      expect(result.current.timelineError).toBe('Not found')
    })

    expect(result.current.timelineLoading).toBe(false)
    expect(result.current.timeline).toBeNull()
    expect(result.current.renderPlanJson).toBeNull()
  })

  it('fetchTimeline handles 5xx error with structured detail.message', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({ detail: { message: 'Internal server error', code: 'SERVER_ERROR' } }),
        { status: 500 },
      ),
    )

    const { result } = renderHook(() => useRenderModal())
    act(() => {
      result.current.fetchTimeline('proj-1')
    })

    await waitFor(() => {
      expect(result.current.timelineError).toBe('Internal server error')
    })
  })

  it('fetchTimeline handles network error', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useRenderModal())
    act(() => {
      result.current.fetchTimeline('proj-1')
    })

    await waitFor(() => {
      expect(result.current.timelineError).toBe('Failed to fetch timeline')
    })
  })

  it('render_plan.total_duration is null if timeline.duration is zero', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({ ...TIMELINE_RESPONSE, duration: 0 }),
        { status: 200 },
      ),
    )

    const { result } = renderHook(() => useRenderModal())
    act(() => {
      result.current.fetchTimeline('proj-1')
    })

    await waitFor(() => {
      expect(result.current.timelineError).toBe('Timeline is empty')
    })

    expect(result.current.timeline).toBeNull()
    expect(result.current.renderPlanJson).toBeNull()
  })

  it('fetchTimeline sets timelineError when duration is negative', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({ ...TIMELINE_RESPONSE, duration: -5 }),
        { status: 200 },
      ),
    )

    const { result } = renderHook(() => useRenderModal())
    act(() => {
      result.current.fetchTimeline('proj-1')
    })

    await waitFor(() => {
      expect(result.current.timelineError).toBe('Timeline is empty')
    })
  })

  it('fetchTimeline aborts previous in-flight request when called again', async () => {
    let resolveFirst!: (r: Response) => void
    const firstPromise = new Promise<Response>((res) => { resolveFirst = res })

    const fetchSpy = vi.spyOn(globalThis, 'fetch')
      .mockImplementationOnce(() => firstPromise)
      .mockResolvedValueOnce(new Response(JSON.stringify(TIMELINE_RESPONSE), { status: 200 }))

    const { result } = renderHook(() => useRenderModal())

    // Start first fetch
    act(() => { result.current.fetchTimeline('proj-1') })
    expect(result.current.timelineLoading).toBe(true)

    // Start second fetch — aborts first
    act(() => { result.current.fetchTimeline('proj-2') })

    // Resolve first (should be ignored since aborted)
    resolveFirst(new Response(JSON.stringify({ ...TIMELINE_RESPONSE, project_id: 'proj-1' }), { status: 200 }))

    await waitFor(() => {
      expect(result.current.timelineLoading).toBe(false)
    })

    expect(fetchSpy).toHaveBeenCalledTimes(2)
    // Second fetch resolved → timeline should be set
    expect(result.current.timeline).not.toBeNull()
  })

  it('resetTimeline clears all state', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(TIMELINE_RESPONSE), { status: 200 }),
    )

    const { result } = renderHook(() => useRenderModal())
    act(() => { result.current.fetchTimeline('proj-1') })

    await waitFor(() => {
      expect(result.current.timeline).not.toBeNull()
    })

    act(() => { result.current.resetTimeline() })

    expect(result.current.timelineLoading).toBe(false)
    expect(result.current.timeline).toBeNull()
    expect(result.current.timelineError).toBeNull()
    expect(result.current.renderPlanJson).toBeNull()
  })
})
