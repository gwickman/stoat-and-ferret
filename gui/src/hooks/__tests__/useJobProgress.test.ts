import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useJobProgress } from '../useJobProgress'
import {
  MockWebSocket,
  mockInstances,
  resetMockInstances,
} from '../../__tests__/mockWebSocket'

beforeEach(() => {
  resetMockInstances()
  vi.stubGlobal('WebSocket', MockWebSocket)
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

function makeProgressEvent(
  jobId: string,
  progress: number,
  status: string = 'running',
): string {
  return JSON.stringify({
    type: 'job_progress',
    payload: { job_id: jobId, progress, status },
    timestamp: new Date().toISOString(),
  })
}

describe('useJobProgress', () => {
  it('returns null state initially', () => {
    const { result } = renderHook(() => useJobProgress('job-1'))

    expect(result.current.progress).toBeNull()
    expect(result.current.status).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('updates progress from matching JOB_PROGRESS events', () => {
    const { result } = renderHook(() => useJobProgress('job-1'))

    act(() => {
      mockInstances[0].simulateOpen()
    })

    act(() => {
      mockInstances[0].simulateMessage(makeProgressEvent('job-1', 0.5))
    })

    expect(result.current.progress).toBe(0.5)
    expect(result.current.status).toBe('running')
  })

  it('ignores events for different job IDs', () => {
    const { result } = renderHook(() => useJobProgress('job-1'))

    act(() => {
      mockInstances[0].simulateOpen()
    })

    act(() => {
      mockInstances[0].simulateMessage(makeProgressEvent('job-2', 0.8))
    })

    expect(result.current.progress).toBeNull()
  })

  it('ignores non-job_progress event types', () => {
    const { result } = renderHook(() => useJobProgress('job-1'))

    act(() => {
      mockInstances[0].simulateOpen()
    })

    act(() => {
      mockInstances[0].simulateMessage(
        JSON.stringify({
          type: 'scan_started',
          payload: { path: '/videos' },
          timestamp: new Date().toISOString(),
        }),
      )
    })

    expect(result.current.progress).toBeNull()
  })

  it('ignores non-JSON messages', () => {
    const { result } = renderHook(() => useJobProgress('job-1'))

    act(() => {
      mockInstances[0].simulateOpen()
    })

    act(() => {
      mockInstances[0].simulateMessage('not json')
    })

    expect(result.current.progress).toBeNull()
  })

  it('tracks progressive updates', () => {
    const { result } = renderHook(() => useJobProgress('job-1'))

    act(() => {
      mockInstances[0].simulateOpen()
    })

    act(() => {
      mockInstances[0].simulateMessage(makeProgressEvent('job-1', 0.25))
    })
    expect(result.current.progress).toBe(0.25)

    act(() => {
      mockInstances[0].simulateMessage(makeProgressEvent('job-1', 0.75))
    })
    expect(result.current.progress).toBe(0.75)

    act(() => {
      mockInstances[0].simulateMessage(makeProgressEvent('job-1', 1.0))
    })
    expect(result.current.progress).toBe(1.0)
  })

  it('returns null state when jobId is null', () => {
    const { result } = renderHook(() => useJobProgress(null))

    act(() => {
      mockInstances[0].simulateOpen()
    })

    act(() => {
      mockInstances[0].simulateMessage(makeProgressEvent('job-1', 0.5))
    })

    expect(result.current.progress).toBeNull()
  })

  it('resets state when jobId changes', () => {
    const { result, rerender } = renderHook(
      ({ jobId }: { jobId: string | null }) => useJobProgress(jobId),
      { initialProps: { jobId: 'job-1' } },
    )

    act(() => {
      mockInstances[0].simulateOpen()
    })

    act(() => {
      mockInstances[0].simulateMessage(makeProgressEvent('job-1', 0.5))
    })
    expect(result.current.progress).toBe(0.5)

    rerender({ jobId: 'job-2' })
    expect(result.current.progress).toBeNull()
  })
})
