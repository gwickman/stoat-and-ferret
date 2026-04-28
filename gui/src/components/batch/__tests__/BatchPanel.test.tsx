import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import BatchPanel from '../BatchPanel'
import { useBatchStore } from '../../../stores/batchStore'

function fillFirstRow(projectId: string, outputPath: string): void {
  fireEvent.change(screen.getByTestId('batch-project-0'), { target: { value: projectId } })
  fireEvent.change(screen.getByTestId('batch-output-0'), { target: { value: outputPath } })
}

beforeEach(() => {
  useBatchStore.getState().reset()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('BatchPanel', () => {
  it('renders the form with one initial entry', () => {
    render(<BatchPanel />)
    expect(screen.getByTestId('batch-panel')).toBeDefined()
    expect(screen.getByTestId('batch-entry-0')).toBeDefined()
    expect(screen.queryByTestId('batch-entry-1')).toBeNull()
  })

  it('adds a new row when "Add Job" is clicked', () => {
    render(<BatchPanel />)
    fireEvent.click(screen.getByTestId('batch-add-row'))
    expect(screen.getByTestId('batch-entry-1')).toBeDefined()
  })

  it('removes a row when the × button is clicked (when more than one row)', () => {
    render(<BatchPanel />)
    fireEvent.click(screen.getByTestId('batch-add-row'))
    expect(screen.getByTestId('batch-entry-1')).toBeDefined()
    fireEvent.click(screen.getByTestId('batch-remove-1'))
    expect(screen.queryByTestId('batch-entry-1')).toBeNull()
  })

  it('keeps the last row visible (cannot remove the only row)', () => {
    render(<BatchPanel />)
    const removeBtn = screen.getByTestId('batch-remove-0') as HTMLButtonElement
    expect(removeBtn.disabled).toBe(true)
  })

  it('shows an inline validation error when no row has project_id and output_path', () => {
    render(<BatchPanel />)
    fireEvent.click(screen.getByTestId('batch-submit'))
    expect(screen.getByTestId('batch-validation-error').textContent).toContain('at least one')
  })

  it('submits the batch and seeds the store with placeholder jobs on 202', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({ batch_id: 'b-100', jobs_queued: 1, status: 'accepted' }),
        { status: 202 },
      ),
    )
    const onSubmitted = vi.fn()
    render(<BatchPanel onBatchSubmitted={onSubmitted} />)
    fillFirstRow('proj-1', '/out/1.mp4')
    fireEvent.click(screen.getByTestId('batch-submit'))
    await waitFor(() => {
      expect(onSubmitted).toHaveBeenCalledWith('b-100')
    })
    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/v1/render/batch',
      expect.objectContaining({ method: 'POST' }),
    )
    const jobs = useBatchStore.getState().jobs
    expect(jobs).toHaveLength(1)
    expect(jobs[0].batch_id).toBe('b-100')
    expect(jobs[0].project_id).toBe('proj-1')
    expect(jobs[0].status).toBe('queued')
  })

  it('shows the server error message on a 422 response and preserves form state', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({ detail: { code: 'BATCH_JOB_LIMIT_EXCEEDED', message: 'too many' } }),
        { status: 422 },
      ),
    )
    render(<BatchPanel />)
    fillFirstRow('proj-1', '/out/1.mp4')
    fireEvent.click(screen.getByTestId('batch-submit'))
    await waitFor(() => {
      expect(screen.getByTestId('batch-submit-error').textContent).toContain('too many')
    })
    const projectInput = screen.getByTestId('batch-project-0') as HTMLInputElement
    expect(projectInput.value).toBe('proj-1')
  })

  it('shows a generic server error on 5xx and preserves form state', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({}), { status: 503 }),
    )
    render(<BatchPanel />)
    fillFirstRow('proj-1', '/out/1.mp4')
    fireEvent.click(screen.getByTestId('batch-submit'))
    await waitFor(() => {
      expect(screen.getByTestId('batch-submit-error').textContent).toMatch(/Server error \(503\)/)
    })
    const projectInput = screen.getByTestId('batch-project-0') as HTMLInputElement
    expect(projectInput.value).toBe('proj-1')
  })

  it('disables submit button while submitting', async () => {
    let resolveFetch: (value: Response) => void = () => {}
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      () => new Promise<Response>((resolve) => {
        resolveFetch = resolve
      }),
    )
    render(<BatchPanel />)
    fillFirstRow('p1', '/out/1.mp4')
    fireEvent.click(screen.getByTestId('batch-submit'))
    await waitFor(() => {
      expect((screen.getByTestId('batch-submit') as HTMLButtonElement).disabled).toBe(true)
    })
    resolveFetch(new Response(
      JSON.stringify({ batch_id: 'b1', jobs_queued: 1, status: 'accepted' }),
      { status: 202 },
    ))
    await waitFor(() => {
      expect((screen.getByTestId('batch-submit') as HTMLButtonElement).disabled).toBe(false)
    })
  })
})
