import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import LibraryPage from '../LibraryPage'
import {
  MockWebSocket,
  mockInstances,
  resetMockInstances,
} from '../../__tests__/mockWebSocket'

vi.mock('../../hooks/useVideos', () => ({
  useVideos: vi.fn().mockReturnValue({
    videos: [],
    total: 0,
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
}))

const mockAnnounce = vi.fn()
vi.mock('../../hooks/useAnnounce', () => ({
  useAnnounce: () => ({ announce: mockAnnounce }),
}))

beforeEach(() => {
  resetMockInstances()
  vi.stubGlobal('WebSocket', MockWebSocket)
  mockAnnounce.mockClear()
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response('{}', { status: 404 }),
  )
})

function renderPage() {
  return render(
    <MemoryRouter>
      <LibraryPage />
    </MemoryRouter>,
  )
}

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

describe('LibraryPage', () => {
  it('renders with role="main" and id="main-content"', () => {
    renderPage()
    const main = screen.getByRole('main')
    expect(main).toHaveAttribute('id', 'main-content')
  })

  it('renders library heading', () => {
    renderPage()
    expect(screen.getByText('Library')).toBeDefined()
  })

  // ---- Dynamic scan announcement tests (FR-002) ----

  it('announces "Scan complete" when scan finishes via WebSocket', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (String(url).includes('/api/v1/videos/scan')) {
        return new Response(JSON.stringify({ job_id: 'scan-1' }), { status: 202 })
      }
      return new Response('{}', { status: 200 })
    })

    renderPage()

    // Open scan modal
    fireEvent.click(screen.getByTestId('scan-button'))

    // Fill in and submit scan
    const input = screen.getByTestId('scan-directory-input')
    fireEvent.change(input, { target: { value: '/videos' } })
    fireEvent.click(screen.getByTestId('scan-submit'))

    await waitFor(() => {
      expect(screen.getByTestId('scan-abort')).toBeDefined()
    })

    // Simulate WebSocket completion
    const ws = mockInstances[0]
    ws.simulateOpen()
    ws.simulateMessage(makeProgressEvent('scan-1', 1.0, 'complete'))

    await waitFor(() => {
      expect(mockAnnounce).toHaveBeenCalledWith('Scan complete')
    })
  })

  it('announces scan error with assertive priority on scan failure via WebSocket', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (String(url).includes('/api/v1/videos/scan')) {
        return new Response(JSON.stringify({ job_id: 'scan-1' }), { status: 202 })
      }
      return new Response('{}', { status: 200 })
    })

    renderPage()

    fireEvent.click(screen.getByTestId('scan-button'))
    const input = screen.getByTestId('scan-directory-input')
    fireEvent.change(input, { target: { value: '/videos' } })
    fireEvent.click(screen.getByTestId('scan-submit'))

    await waitFor(() => {
      expect(screen.getByTestId('scan-abort')).toBeDefined()
    })

    const ws = mockInstances[0]
    ws.simulateOpen()
    ws.simulateMessage(makeProgressEvent('scan-1', 0.3, 'failed', 'Permission denied'))

    await waitFor(() => {
      expect(mockAnnounce).toHaveBeenCalledWith('Error: Permission denied', 'assertive')
    })
  })

  it('announces scan error with assertive priority on scan request failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ message: 'Invalid directory' }), { status: 400 }),
    )

    renderPage()

    fireEvent.click(screen.getByTestId('scan-button'))
    const input = screen.getByTestId('scan-directory-input')
    fireEvent.change(input, { target: { value: '/bad/path' } })
    fireEvent.click(screen.getByTestId('scan-submit'))

    await waitFor(() => {
      expect(mockAnnounce).toHaveBeenCalledWith('Error: Invalid directory', 'assertive')
    })
  })
})
