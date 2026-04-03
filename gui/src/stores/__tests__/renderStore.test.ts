import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useRenderStore } from '../renderStore'
import type { RenderJob, QueueStatus } from '../renderStore'

const mockJob: RenderJob = {
  id: 'job-1',
  project_id: 'proj-1',
  status: 'pending',
  output_path: '/out/video.mp4',
  output_format: 'mp4',
  quality_preset: 'standard',
  progress: 0,
  error_message: null,
  retry_count: 0,
  created_at: '2025-06-01T00:00:00Z',
  updated_at: '2025-06-01T00:00:00Z',
  completed_at: null,
}

const mockQueueStatus: QueueStatus = {
  active_count: 1,
  pending_count: 2,
  max_concurrent: 4,
  max_queue_depth: 20,
  disk_available_bytes: 500_000_000,
  disk_total_bytes: 1_000_000_000,
  completed_today: 5,
  failed_today: 1,
}

beforeEach(() => {
  vi.restoreAllMocks()
  useRenderStore.getState().reset()
})

describe('renderStore', () => {
  // -- Fetch actions --

  it('fetchJobs populates jobs from API', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ items: [mockJob], total: 1, limit: 50, offset: 0 }), { status: 200 }),
    )

    await useRenderStore.getState().fetchJobs()

    const state = useRenderStore.getState()
    expect(state.jobs).toHaveLength(1)
    expect(state.jobs[0].id).toBe('job-1')
    expect(state.isLoading).toBe(false)
    expect(state.error).toBeNull()
  })

  it('fetchQueueStatus populates queueStatus from API', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify(mockQueueStatus), { status: 200 }),
    )

    await useRenderStore.getState().fetchQueueStatus()

    const state = useRenderStore.getState()
    expect(state.queueStatus).toEqual(mockQueueStatus)
    expect(state.isLoading).toBe(false)
  })

  it('fetchEncoders populates encoders from API', async () => {
    const encoders = [{ name: 'libx264', codec: 'h264', is_hardware: false, encoder_type: 'software', description: 'H.264', detected_at: '2025-06-01T00:00:00Z' }]
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ encoders, cached: false }), { status: 200 }),
    )

    await useRenderStore.getState().fetchEncoders()

    const state = useRenderStore.getState()
    expect(state.encoders).toHaveLength(1)
    expect(state.encoders[0].name).toBe('libx264')
    expect(state.isLoading).toBe(false)
  })

  it('fetchFormats populates formats from API', async () => {
    const formats = [{ format: 'mp4', extension: '.mp4', mime_type: 'video/mp4', codecs: [], supports_hw_accel: false, supports_two_pass: true, supports_alpha: false }]
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ formats }), { status: 200 }),
    )

    await useRenderStore.getState().fetchFormats()

    const state = useRenderStore.getState()
    expect(state.formats).toHaveLength(1)
    expect(state.formats[0].format).toBe('mp4')
    expect(state.isLoading).toBe(false)
  })

  it('sets error state on fetch failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response('', { status: 500 }),
    )

    await useRenderStore.getState().fetchJobs()

    const state = useRenderStore.getState()
    expect(state.error).toBe('Fetch jobs failed: 500')
    expect(state.isLoading).toBe(false)
  })

  // -- Mutation actions --

  it('updateJob adds a new job when not present', () => {
    useRenderStore.getState().updateJob(mockJob)

    expect(useRenderStore.getState().jobs).toHaveLength(1)
    expect(useRenderStore.getState().jobs[0].id).toBe('job-1')
  })

  it('updateJob merges into existing job by id', () => {
    useRenderStore.getState().updateJob(mockJob)
    useRenderStore.getState().updateJob({ id: 'job-1', status: 'running' })

    const jobs = useRenderStore.getState().jobs
    expect(jobs).toHaveLength(1)
    expect(jobs[0].status).toBe('running')
    expect(jobs[0].output_format).toBe('mp4') // unchanged field preserved
  })

  it('removeJob removes a job by id', () => {
    useRenderStore.getState().updateJob(mockJob)
    useRenderStore.getState().removeJob('job-1')

    expect(useRenderStore.getState().jobs).toHaveLength(0)
  })

  it('setProgress updates progress on matching job', () => {
    useRenderStore.getState().updateJob(mockJob)
    useRenderStore.getState().setProgress('job-1', 0.75)

    expect(useRenderStore.getState().jobs[0].progress).toBe(0.75)
  })

  it('setQueueStatus performs partial merge preserving REST-only fields', () => {
    // Simulate REST fetch populating all 8 fields
    useRenderStore.setState({ queueStatus: mockQueueStatus })

    // WS update with only 4 count fields
    useRenderStore.getState().setQueueStatus({
      active_count: 3,
      pending_count: 5,
      max_concurrent: 4,
      max_queue_depth: 20,
    })

    const qs = useRenderStore.getState().queueStatus!
    // Updated fields
    expect(qs.active_count).toBe(3)
    expect(qs.pending_count).toBe(5)
    // REST-only fields preserved
    expect(qs.disk_available_bytes).toBe(500_000_000)
    expect(qs.disk_total_bytes).toBe(1_000_000_000)
    expect(qs.completed_today).toBe(5)
    expect(qs.failed_today).toBe(1)
  })

  it('reset returns all fields to initial values', () => {
    useRenderStore.getState().updateJob(mockJob)
    useRenderStore.setState({ queueStatus: mockQueueStatus, isLoading: true, error: 'oops' })

    useRenderStore.getState().reset()

    const state = useRenderStore.getState()
    expect(state.jobs).toHaveLength(0)
    expect(state.queueStatus).toBeNull()
    expect(state.encoders).toHaveLength(0)
    expect(state.formats).toHaveLength(0)
    expect(state.isLoading).toBe(false)
    expect(state.error).toBeNull()
  })
})
