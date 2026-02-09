import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ScanModal from '../ScanModal'

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('ScanModal', () => {
  it('does not render when closed', () => {
    render(
      <ScanModal open={false} onClose={vi.fn()} onScanComplete={vi.fn()} />,
    )

    expect(screen.queryByTestId('scan-modal-overlay')).toBeNull()
  })

  it('renders when open with directory input and submit button', () => {
    render(
      <ScanModal open={true} onClose={vi.fn()} onScanComplete={vi.fn()} />,
    )

    expect(screen.getByTestId('scan-modal-overlay')).toBeDefined()
    expect(screen.getByTestId('scan-directory-input')).toBeDefined()
    expect(screen.getByTestId('scan-submit')).toBeDefined()
    expect(screen.getByTestId('scan-cancel')).toBeDefined()
  })

  it('submit button is disabled when directory is empty', () => {
    render(
      <ScanModal open={true} onClose={vi.fn()} onScanComplete={vi.fn()} />,
    )

    const submit = screen.getByTestId('scan-submit') as HTMLButtonElement
    expect(submit.disabled).toBe(true)
  })

  it('triggers scan API call on submit', async () => {
    const onScanComplete = vi.fn()
    const completedJob = {
      job_id: 'job-1',
      status: 'completed',
      progress: 1.0,
      result: { scanned: 5 },
      error: null,
    }
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (String(url).includes('/api/v1/videos/scan')) {
        return new Response(JSON.stringify({ job_id: 'job-1' }), {
          status: 202,
        })
      }
      return new Response(JSON.stringify(completedJob), { status: 200 })
    })

    render(
      <ScanModal
        open={true}
        onClose={vi.fn()}
        onScanComplete={onScanComplete}
      />,
    )

    const input = screen.getByTestId('scan-directory-input')
    fireEvent.change(input, { target: { value: '/videos' } })

    const submit = screen.getByTestId('scan-submit')
    fireEvent.click(submit)

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/v1/videos/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: '/videos', recursive: true }),
      })
    })

    // Wait for polling to find completion (poll fires at 1s intervals)
    await waitFor(
      () => {
        expect(screen.getByTestId('scan-complete')).toBeDefined()
      },
      { timeout: 3000 },
    )

    expect(onScanComplete).toHaveBeenCalled()
  })

  it('shows error when scan request fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(
        JSON.stringify({ message: 'Invalid directory' }),
        { status: 400 },
      ),
    )

    render(
      <ScanModal open={true} onClose={vi.fn()} onScanComplete={vi.fn()} />,
    )

    const input = screen.getByTestId('scan-directory-input')
    fireEvent.change(input, { target: { value: '/bad/path' } })

    const submit = screen.getByTestId('scan-submit')
    fireEvent.click(submit)

    await waitFor(() => {
      expect(screen.getByTestId('scan-error')).toBeDefined()
      expect(screen.getByTestId('scan-error').textContent).toBe(
        'Invalid directory',
      )
    })
  })
})
