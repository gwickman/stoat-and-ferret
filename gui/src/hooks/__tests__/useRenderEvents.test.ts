import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useRenderEvents } from '../useRenderEvents'
import { useRenderStore } from '../../stores/renderStore'
import type { QueueStatus } from '../../stores/renderStore'
import {
  MockWebSocket,
  mockInstances,
  resetMockInstances,
} from '../../__tests__/mockWebSocket'

beforeEach(() => {
  resetMockInstances()
  vi.stubGlobal('WebSocket', MockWebSocket)
  vi.useFakeTimers()
  useRenderStore.getState().reset()
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

/** Build a serialized WS event message. */
function makeEvent(type: string, payload: Record<string, unknown>): string {
  return JSON.stringify({ type, payload, timestamp: new Date().toISOString() })
}

describe('useRenderEvents', () => {
  // -- Lifecycle event dispatching --

  it('dispatches render_queued to updateJob', () => {
    renderHook(() => useRenderEvents())
    act(() => { mockInstances[0].simulateOpen() })

    act(() => {
      mockInstances[0].simulateMessage(
        makeEvent('render_queued', { job_id: 'j1', project_id: 'p1', status: 'pending' }),
      )
    })

    const jobs = useRenderStore.getState().jobs
    expect(jobs).toHaveLength(1)
    expect(jobs[0].id).toBe('j1')
    expect(jobs[0].status).toBe('pending')
  })

  it('dispatches render_started to updateJob', () => {
    renderHook(() => useRenderEvents())
    act(() => { mockInstances[0].simulateOpen() })

    act(() => {
      mockInstances[0].simulateMessage(
        makeEvent('render_started', { job_id: 'j1', project_id: 'p1', status: 'running' }),
      )
    })

    expect(useRenderStore.getState().jobs[0].status).toBe('running')
  })

  it('dispatches render_completed to updateJob', () => {
    renderHook(() => useRenderEvents())
    act(() => { mockInstances[0].simulateOpen() })

    act(() => {
      mockInstances[0].simulateMessage(
        makeEvent('render_completed', { job_id: 'j1', project_id: 'p1', status: 'completed' }),
      )
    })

    expect(useRenderStore.getState().jobs[0].status).toBe('completed')
  })

  it('dispatches render_failed to updateJob', () => {
    renderHook(() => useRenderEvents())
    act(() => { mockInstances[0].simulateOpen() })

    act(() => {
      mockInstances[0].simulateMessage(
        makeEvent('render_failed', { job_id: 'j1', project_id: 'p1', status: 'failed' }),
      )
    })

    expect(useRenderStore.getState().jobs[0].status).toBe('failed')
  })

  it('dispatches render_cancelled to updateJob', () => {
    renderHook(() => useRenderEvents())
    act(() => { mockInstances[0].simulateOpen() })

    act(() => {
      mockInstances[0].simulateMessage(
        makeEvent('render_cancelled', { job_id: 'j1', project_id: 'p1', status: 'cancelled' }),
      )
    })

    expect(useRenderStore.getState().jobs[0].status).toBe('cancelled')
  })

  // -- Progress and queue status --

  it('dispatches render_progress to setProgress', () => {
    // Pre-populate a job so setProgress has something to update
    useRenderStore.getState().updateJob({
      id: 'j1',
      project_id: 'p1',
      status: 'running',
      output_path: '',
      output_format: 'mp4',
      quality_preset: 'standard',
      progress: 0,
      error_message: null,
      retry_count: 0,
      created_at: '',
      updated_at: '',
      completed_at: null,
    })

    renderHook(() => useRenderEvents())
    act(() => { mockInstances[0].simulateOpen() })

    act(() => {
      mockInstances[0].simulateMessage(
        makeEvent('render_progress', { job_id: 'j1', progress: 0.42 }),
      )
    })

    expect(useRenderStore.getState().jobs[0].progress).toBe(0.42)
  })

  it('dispatches render_frame_available to setProgress', () => {
    useRenderStore.getState().updateJob({
      id: 'j1',
      project_id: 'p1',
      status: 'running',
      output_path: '',
      output_format: 'mp4',
      quality_preset: 'standard',
      progress: 0,
      error_message: null,
      retry_count: 0,
      created_at: '',
      updated_at: '',
      completed_at: null,
    })

    renderHook(() => useRenderEvents())
    act(() => { mockInstances[0].simulateOpen() })

    act(() => {
      mockInstances[0].simulateMessage(
        makeEvent('render_frame_available', { job_id: 'j1', frame_url: '/frame.jpg', resolution: '540p', progress: 0.6 }),
      )
    })

    expect(useRenderStore.getState().jobs[0].progress).toBe(0.6)
  })

  it('dispatches render_queue_status to setQueueStatus with partial merge', () => {
    // Pre-populate with full REST data
    const fullStatus: QueueStatus = {
      active_count: 1,
      pending_count: 2,
      max_concurrent: 4,
      max_queue_depth: 20,
      disk_available_bytes: 500_000_000,
      disk_total_bytes: 1_000_000_000,
      completed_today: 5,
      failed_today: 1,
    }
    useRenderStore.setState({ queueStatus: fullStatus })

    renderHook(() => useRenderEvents())
    act(() => { mockInstances[0].simulateOpen() })

    // WS sends only 4 fields
    act(() => {
      mockInstances[0].simulateMessage(
        makeEvent('render_queue_status', {
          active_count: 3,
          pending_count: 7,
          max_concurrent: 4,
          max_queue_depth: 20,
        }),
      )
    })

    const qs = useRenderStore.getState().queueStatus!
    expect(qs.active_count).toBe(3)
    expect(qs.pending_count).toBe(7)
    // REST-only fields preserved
    expect(qs.disk_available_bytes).toBe(500_000_000)
    expect(qs.completed_today).toBe(5)
  })

  // -- Filtering --

  it('ignores non-render events', () => {
    renderHook(() => useRenderEvents())
    act(() => { mockInstances[0].simulateOpen() })

    act(() => {
      mockInstances[0].simulateMessage(
        makeEvent('job_progress', { job_id: 'j1', progress: 0.5, status: 'running' }),
      )
    })

    expect(useRenderStore.getState().jobs).toHaveLength(0)
  })

  it('ignores malformed JSON messages', () => {
    renderHook(() => useRenderEvents())
    act(() => { mockInstances[0].simulateOpen() })

    act(() => {
      mockInstances[0].simulateMessage('not valid json {{')
    })

    // No crash, store unchanged
    expect(useRenderStore.getState().jobs).toHaveLength(0)
  })

  // -- Reconnection re-fetch --

  it('re-fetches jobs and queue status on reconnection', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
    fetchSpy.mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 0, limit: 50, offset: 0 }), { status: 200 }),
    )

    renderHook(() => useRenderEvents())

    // Simulate connected
    act(() => { mockInstances[0].simulateOpen() })

    // Simulate disconnect (triggers reconnecting state)
    act(() => { mockInstances[0].simulateClose() })

    // Advance timers to trigger reconnect
    act(() => { vi.advanceTimersByTime(1000) })

    // New WS instance connects
    act(() => { mockInstances[1].simulateOpen() })

    // Re-fetch should have been triggered
    expect(fetchSpy).toHaveBeenCalledWith('/api/v1/render')
    expect(fetchSpy).toHaveBeenCalledWith('/api/v1/render/queue')
  })
})
