/**
 * BL-702: omitted fields preserve prior store values.
 * Tests that render_progress payloads omitting preserve-group fields
 * (frameCount, fps, encoderName, encoderType) preserve prior store values
 * rather than clearing them to null.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useRenderEvents } from '../useRenderEvents'
import { useRenderStore } from '../../stores/renderStore'
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

function makeEvent(type: string, payload: Record<string, unknown>): string {
  return JSON.stringify({ type, payload, timestamp: new Date().toISOString() })
}

describe('useRenderEvents — omit-vs-null forwarding (BL-702)', () => {
  it('preserves prior store values for omitted preserve-group fields', () => {
    // Seed the store with a job that has existing frame-encoder metadata
    useRenderStore.getState().updateJob({
      id: 'j1',
      project_id: 'p1',
      status: 'running',
      output_path: '',
      output_format: 'mp4',
      quality_preset: 'standard',
      progress: 0.1,
      eta_seconds: null,
      speed_ratio: null,
      frame_count: 1024,
      fps: 29.97,
      encoder_name: 'libx264',
      encoder_type: 'software',
      error_message: null,
      retry_count: 0,
      created_at: '',
      updated_at: '',
      completed_at: null,
    })

    renderHook(() => useRenderEvents())
    act(() => { mockInstances[0].simulateOpen() })

    // Dispatch a render_progress payload that includes job_id, progress,
    // eta_seconds, speed_ratio but OMITS frame_count, fps, encoder_name,
    // encoder_type — the preserve-prior-value group.
    act(() => {
      mockInstances[0].simulateMessage(
        makeEvent('render_progress', {
          job_id: 'j1',
          progress: 0.5,
          eta_seconds: 10.0,
          speed_ratio: 1.2,
          // frame_count, fps, encoder_name, encoder_type intentionally absent
        }),
      )
    })

    const job = useRenderStore.getState().jobs[0]
    // Always-overwrite group must be updated
    expect(job.progress).toBe(0.5)
    expect(job.eta_seconds).toBe(10.0)
    expect(job.speed_ratio).toBe(1.2)
    // Preserve-prior-value group must retain the seeded values (not cleared to null)
    expect(job.frame_count).toBe(1024)
    expect(job.fps).toBe(29.97)
    expect(job.encoder_name).toBe('libx264')
    expect(job.encoder_type).toBe('software')
  })
})
