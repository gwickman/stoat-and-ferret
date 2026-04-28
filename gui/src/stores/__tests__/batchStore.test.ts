import { describe, it, expect, beforeEach } from 'vitest'
import { TERMINAL_BATCH_STATUSES, useBatchStore, type BatchJob } from '../batchStore'

function makeJob(overrides: Partial<BatchJob> & { job_id: string }): BatchJob {
  return {
    batch_id: 'b-1',
    project_id: 'p-1',
    status: 'queued',
    progress: 0,
    error: null,
    submitted_at: 1700000000000,
    ...overrides,
  }
}

beforeEach(() => {
  useBatchStore.getState().reset()
})

describe('batchStore', () => {
  it('initializes with empty jobs and idle submit state', () => {
    const state = useBatchStore.getState()
    expect(state.jobs).toEqual([])
    expect(state.submitting).toBe(false)
    expect(state.submitError).toBeNull()
  })

  describe('addJob', () => {
    it('appends a new job to the list', () => {
      useBatchStore.getState().addJob(makeJob({ job_id: 'j1' }))
      expect(useBatchStore.getState().jobs).toHaveLength(1)
      expect(useBatchStore.getState().jobs[0].job_id).toBe('j1')
    })

    it('merges fields when a job with the same id is added twice', () => {
      useBatchStore.getState().addJob(makeJob({ job_id: 'j1', progress: 0 }))
      useBatchStore.getState().addJob(makeJob({ job_id: 'j1', progress: 0.5, status: 'running' }))
      const jobs = useBatchStore.getState().jobs
      expect(jobs).toHaveLength(1)
      expect(jobs[0].progress).toBe(0.5)
      expect(jobs[0].status).toBe('running')
    })
  })

  describe('updateJob', () => {
    it('updates status and progress on an existing job', () => {
      useBatchStore.getState().addJob(makeJob({ job_id: 'j1' }))
      useBatchStore.getState().updateJob({ job_id: 'j1', status: 'running', progress: 0.25 })
      const job = useBatchStore.getState().jobs[0]
      expect(job.status).toBe('running')
      expect(job.progress).toBe(0.25)
    })

    it('is a no-op when the target job does not exist', () => {
      useBatchStore.getState().addJob(makeJob({ job_id: 'j1' }))
      useBatchStore.getState().updateJob({ job_id: 'missing', status: 'running' })
      expect(useBatchStore.getState().jobs).toHaveLength(1)
      expect(useBatchStore.getState().jobs[0].status).toBe('queued')
    })

    it('preserves progress when an update would decrease it on a non-queued job (INV-003)', () => {
      useBatchStore.getState().addJob(makeJob({ job_id: 'j1', status: 'running', progress: 0.5 }))
      useBatchStore.getState().updateJob({ job_id: 'j1', status: 'running', progress: 0.1 })
      expect(useBatchStore.getState().jobs[0].progress).toBe(0.5)
    })

    it('allows setting an explicit error string', () => {
      useBatchStore.getState().addJob(makeJob({ job_id: 'j1' }))
      useBatchStore.getState().updateJob({ job_id: 'j1', status: 'failed', error: 'render failed' })
      const job = useBatchStore.getState().jobs[0]
      expect(job.error).toBe('render failed')
    })

    it('drives queued -> running -> completed transitions', () => {
      useBatchStore.getState().addJob(makeJob({ job_id: 'j1', status: 'queued' }))
      useBatchStore.getState().updateJob({ job_id: 'j1', status: 'running', progress: 0.5 })
      useBatchStore.getState().updateJob({ job_id: 'j1', status: 'completed', progress: 1.0 })
      const job = useBatchStore.getState().jobs[0]
      expect(job.status).toBe('completed')
      expect(job.progress).toBe(1.0)
    })
  })

  describe('removeJob', () => {
    it('removes a job by id', () => {
      useBatchStore.getState().addJob(makeJob({ job_id: 'j1' }))
      useBatchStore.getState().addJob(makeJob({ job_id: 'j2' }))
      useBatchStore.getState().removeJob('j1')
      const ids = useBatchStore.getState().jobs.map((j) => j.job_id)
      expect(ids).toEqual(['j2'])
    })
  })

  describe('submit state', () => {
    it('sets and clears submitting flag', () => {
      useBatchStore.getState().setSubmitting(true)
      expect(useBatchStore.getState().submitting).toBe(true)
      useBatchStore.getState().setSubmitting(false)
      expect(useBatchStore.getState().submitting).toBe(false)
    })

    it('sets and clears submit error', () => {
      useBatchStore.getState().setSubmitError('boom')
      expect(useBatchStore.getState().submitError).toBe('boom')
      useBatchStore.getState().setSubmitError(null)
      expect(useBatchStore.getState().submitError).toBeNull()
    })
  })

  it('reset returns the store to initial state', () => {
    useBatchStore.getState().addJob(makeJob({ job_id: 'j1' }))
    useBatchStore.getState().setSubmitting(true)
    useBatchStore.getState().setSubmitError('x')
    useBatchStore.getState().reset()
    const state = useBatchStore.getState()
    expect(state.jobs).toEqual([])
    expect(state.submitting).toBe(false)
    expect(state.submitError).toBeNull()
  })
})

describe('TERMINAL_BATCH_STATUSES', () => {
  it('contains exactly completed, failed, cancelled', () => {
    expect(TERMINAL_BATCH_STATUSES.has('completed')).toBe(true)
    expect(TERMINAL_BATCH_STATUSES.has('failed')).toBe(true)
    expect(TERMINAL_BATCH_STATUSES.has('cancelled')).toBe(true)
    expect(TERMINAL_BATCH_STATUSES.has('queued')).toBe(false)
    expect(TERMINAL_BATCH_STATUSES.has('running')).toBe(false)
  })
})

describe('session-only persistence (NFR-002)', () => {
  it('does not write to localStorage when state changes', () => {
    const before = JSON.stringify(localStorage)
    useBatchStore.getState().addJob(makeJob({ job_id: 'j1' }))
    useBatchStore.getState().updateJob({ job_id: 'j1', status: 'running', progress: 0.4 })
    const after = JSON.stringify(localStorage)
    expect(after).toBe(before)
  })

  it('does not write to sessionStorage when state changes', () => {
    const before = JSON.stringify(sessionStorage)
    useBatchStore.getState().addJob(makeJob({ job_id: 'j1' }))
    useBatchStore.getState().updateJob({ job_id: 'j1', status: 'running', progress: 0.4 })
    const after = JSON.stringify(sessionStorage)
    expect(after).toBe(before)
  })
})
