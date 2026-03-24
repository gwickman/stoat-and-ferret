import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import ScanModal from '../ScanModal'
import {
  MockWebSocket,
  mockInstances,
  resetMockInstances,
} from '../../__tests__/mockWebSocket'

function makeProgressEvent(
  jobId: string,
  progress: number,
  status: string = 'running',
  error: string | null = null,
): string {
  return JSON.stringify({
    type: 'job_progress',
    payload: { job_id: jobId, progress, status, ...(error ? { error } : {}) },
    timestamp: new Date().toISOString(),
  })
}

beforeEach(() => {
  resetMockInstances()
  vi.stubGlobal('WebSocket', MockWebSocket)
  vi.restoreAllMocks()
})

afterEach(() => {
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

  it('triggers scan API call on submit and completes via WebSocket', async () => {
    const onScanComplete = vi.fn()
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (String(url).includes('/api/v1/videos/scan')) {
        return new Response(JSON.stringify({ job_id: 'job-1' }), {
          status: 202,
        })
      }
      return new Response('{}', { status: 200 })
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

    // Simulate WebSocket progress then completion
    const ws = mockInstances[0]
    ws.simulateOpen()
    ws.simulateMessage(makeProgressEvent('job-1', 0.5))
    ws.simulateMessage(makeProgressEvent('job-1', 1.0, 'complete'))

    await waitFor(() => {
      expect(screen.getByTestId('scan-complete')).toBeDefined()
    })

    expect(onScanComplete).toHaveBeenCalled()
  })

  it('shows abort button during active scan', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (String(url).includes('/api/v1/videos/scan')) {
        return new Response(JSON.stringify({ job_id: 'job-1' }), {
          status: 202,
        })
      }
      return new Response('{}', { status: 200 })
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
      return new Response('{}', { status: 200 })
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

  it('shows cancelled state when scan is cancelled via WebSocket', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
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
      return new Response('{}', { status: 200 })
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

    // Simulate WebSocket cancelled event
    const ws = mockInstances[0]
    ws.simulateOpen()
    ws.simulateMessage(makeProgressEvent('job-1', 0.3))
    ws.simulateMessage(makeProgressEvent('job-1', 0.5, 'cancelled'))

    await waitFor(() => {
      expect(screen.getByTestId('scan-cancelled')).toBeDefined()
    })

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

  it('completes scan flow: receives progress then complete via WebSocket', async () => {
    const onScanComplete = vi.fn()

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (String(url).includes('/api/v1/videos/scan')) {
        return new Response(JSON.stringify({ job_id: 'job-2' }), {
          status: 202,
        })
      }
      return new Response('{}', { status: 200 })
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
    fireEvent.click(screen.getByTestId('scan-submit'))

    await waitFor(() => {
      expect(screen.getByTestId('scan-abort')).toBeDefined()
    })

    // Simulate WebSocket progress updates
    const ws = mockInstances[0]
    ws.simulateOpen()
    ws.simulateMessage(makeProgressEvent('job-2', 0.5))
    ws.simulateMessage(makeProgressEvent('job-2', 1.0, 'complete'))

    // Wait for completion state
    await waitFor(() => {
      expect(screen.getByTestId('scan-complete')).toBeDefined()
    })

    // onScanComplete callback should have fired
    expect(onScanComplete).toHaveBeenCalled()

    // Submit button should be gone (complete state)
    expect(screen.queryByTestId('scan-submit')).toBeNull()

    // Close button should show "Close" text
    expect(screen.getByTestId('scan-cancel').textContent).toBe('Close')
  })

  it('shows error with message when scan times out via WebSocket', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (String(url).includes('/api/v1/videos/scan')) {
        return new Response(JSON.stringify({ job_id: 'job-1' }), {
          status: 202,
        })
      }
      return new Response('{}', { status: 200 })
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

    // Simulate WebSocket timeout event
    const ws = mockInstances[0]
    ws.simulateOpen()
    ws.simulateMessage(makeProgressEvent('job-1', 0.5, 'timeout', 'Job timed out after 300.0s'))

    await waitFor(() => {
      expect(screen.getByTestId('scan-error')).toBeDefined()
    })

    expect(screen.getByTestId('scan-error').textContent).toBe(
      'Job timed out after 300.0s',
    )
  })

  it('does not make HTTP polling requests after scan starts', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (String(url).includes('/api/v1/videos/scan')) {
        return new Response(JSON.stringify({ job_id: 'job-1' }), {
          status: 202,
        })
      }
      return new Response('{}', { status: 200 })
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

    // Complete via WebSocket
    const ws = mockInstances[0]
    ws.simulateOpen()
    ws.simulateMessage(makeProgressEvent('job-1', 1.0, 'complete'))

    await waitFor(() => {
      expect(screen.getByTestId('scan-complete')).toBeDefined()
    })

    // Verify no polling requests were made to /api/v1/jobs/{id}
    const jobStatusCalls = fetchSpy.mock.calls.filter(
      (call) => String(call[0]).match(/\/api\/v1\/jobs\/[^/]+$/)
    )
    expect(jobStatusCalls).toHaveLength(0)
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

  it('shows progress percentage from WebSocket events', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (String(url).includes('/api/v1/videos/scan')) {
        return new Response(JSON.stringify({ job_id: 'job-1' }), {
          status: 202,
        })
      }
      return new Response('{}', { status: 200 })
    })

    render(
      <ScanModal open={true} onClose={vi.fn()} onScanComplete={vi.fn()} />,
    )

    const input = screen.getByTestId('scan-directory-input')
    fireEvent.change(input, { target: { value: '/videos' } })
    fireEvent.click(screen.getByTestId('scan-submit'))

    await waitFor(() => {
      expect(screen.getByTestId('scan-progress')).toBeDefined()
    })

    // Simulate progress update via WebSocket
    const ws = mockInstances[0]
    ws.simulateOpen()
    ws.simulateMessage(makeProgressEvent('job-1', 0.75))

    await waitFor(() => {
      expect(screen.getByText('75%')).toBeDefined()
    })
  })
})
