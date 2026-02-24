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

  it('shows abort button during active scan', async () => {
    // Mock: scan submission succeeds, but polling returns running status
    const runningJob = {
      job_id: 'job-1',
      status: 'running',
      progress: 0.5,
      result: null,
      error: null,
    }
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (String(url).includes('/api/v1/videos/scan')) {
        return new Response(JSON.stringify({ job_id: 'job-1' }), {
          status: 202,
        })
      }
      return new Response(JSON.stringify(runningJob), { status: 200 })
    })

    render(
      <ScanModal open={true} onClose={vi.fn()} onScanComplete={vi.fn()} />,
    )

    const input = screen.getByTestId('scan-directory-input')
    fireEvent.change(input, { target: { value: '/videos' } })

    const submit = screen.getByTestId('scan-submit')
    fireEvent.click(submit)

    await waitFor(() => {
      expect(screen.getByTestId('scan-abort')).toBeDefined()
    })

    const abortBtn = screen.getByTestId('scan-abort')
    expect(abortBtn.textContent).toBe('Abort Scan')
  })

  it('abort button calls cancel endpoint', async () => {
    const runningJob = {
      job_id: 'job-1',
      status: 'running',
      progress: 0.5,
      result: null,
      error: null,
    }
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (String(url).includes('/api/v1/videos/scan')) {
        return new Response(JSON.stringify({ job_id: 'job-1' }), {
          status: 202,
        })
      }
      if (String(url).includes('/cancel')) {
        return new Response(JSON.stringify({ job_id: 'job-1', status: 'cancelled' }), {
          status: 200,
        })
      }
      return new Response(JSON.stringify(runningJob), { status: 200 })
    })

    render(
      <ScanModal open={true} onClose={vi.fn()} onScanComplete={vi.fn()} />,
    )

    const input = screen.getByTestId('scan-directory-input')
    fireEvent.change(input, { target: { value: '/videos' } })
    fireEvent.click(screen.getByTestId('scan-submit'))

    await waitFor(() => {
      expect(screen.getByTestId('scan-abort')).toBeDefined()
    })

    fireEvent.click(screen.getByTestId('scan-abort'))

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        '/api/v1/jobs/job-1/cancel',
        { method: 'POST' },
      )
    })
  })

  it('shows cancelled state when scan is cancelled', async () => {
    let pollCount = 0
    const cancelledJob = {
      job_id: 'job-1',
      status: 'cancelled',
      progress: 0.5,
      result: { scanned: 2, new: 2, updated: 0, skipped: 0, errors: [] },
      error: null,
    }
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (String(url).includes('/api/v1/videos/scan')) {
        return new Response(JSON.stringify({ job_id: 'job-1' }), {
          status: 202,
        })
      }
      if (String(url).includes('/cancel')) {
        return new Response(JSON.stringify(cancelledJob), { status: 200 })
      }
      pollCount++
      // First poll returns running, subsequent returns cancelled
      if (pollCount <= 1) {
        return new Response(
          JSON.stringify({ job_id: 'job-1', status: 'running', progress: 0.3, result: null, error: null }),
          { status: 200 },
        )
      }
      return new Response(JSON.stringify(cancelledJob), { status: 200 })
    })

    render(
      <ScanModal open={true} onClose={vi.fn()} onScanComplete={vi.fn()} />,
    )

    const input = screen.getByTestId('scan-directory-input')
    fireEvent.change(input, { target: { value: '/videos' } })
    fireEvent.click(screen.getByTestId('scan-submit'))

    await waitFor(
      () => {
        expect(screen.getByTestId('scan-cancelled')).toBeDefined()
      },
      { timeout: 5000 },
    )

    expect(screen.getByTestId('scan-cancelled').textContent).toBe(
      'Scan cancelled. Partial results have been saved.',
    )
  })

  it('renders browse button when open', () => {
    render(
      <ScanModal open={true} onClose={vi.fn()} onScanComplete={vi.fn()} />,
    )

    expect(screen.getByTestId('scan-browse-button')).toBeDefined()
    expect(screen.getByTestId('scan-browse-button').textContent).toBe('Browse')
  })

  it('opens DirectoryBrowser when browse button clicked', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (String(url).includes('/api/v1/filesystem/directories')) {
        return new Response(
          JSON.stringify({ path: '/home/user', directories: [] }),
          { status: 200 },
        )
      }
      return new Response('{}', { status: 200 })
    })

    render(
      <ScanModal open={true} onClose={vi.fn()} onScanComplete={vi.fn()} />,
    )

    fireEvent.click(screen.getByTestId('scan-browse-button'))

    await waitFor(() => {
      expect(screen.getByTestId('directory-browser-overlay')).toBeDefined()
    })
  })

  it('populates path input when directory is selected from browser', async () => {
    const mockDirs = {
      path: '/home/user',
      directories: [
        { name: 'Videos', path: '/home/user/Videos' },
      ],
    }

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (String(url).includes('/api/v1/filesystem/directories')) {
        return new Response(JSON.stringify(mockDirs), { status: 200 })
      }
      return new Response('{}', { status: 200 })
    })

    render(
      <ScanModal open={true} onClose={vi.fn()} onScanComplete={vi.fn()} />,
    )

    // Open the browser
    fireEvent.click(screen.getByTestId('scan-browse-button'))

    await waitFor(() => {
      expect(screen.getByTestId('directory-browser-overlay')).toBeDefined()
    })

    // Click "Select This Directory" to choose current path
    fireEvent.click(screen.getByTestId('directory-browser-select'))

    // Browser should close
    await waitFor(() => {
      expect(screen.queryByTestId('directory-browser-overlay')).toBeNull()
    })

    // Path input should be populated
    const input = screen.getByTestId('scan-directory-input') as HTMLInputElement
    expect(input.value).toBe('/home/user')
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
