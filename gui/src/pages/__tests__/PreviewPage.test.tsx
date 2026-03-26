import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import PreviewPage from '../PreviewPage'
import { usePreviewStore } from '../../stores/previewStore'
import { useProjectStore } from '../../stores/projectStore'

beforeEach(() => {
  vi.restoreAllMocks()
  usePreviewStore.getState().reset()
  useProjectStore.setState({ selectedProjectId: null })
  // Default: suppress any fetch calls from useEffect
  vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('No mock'))
})

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/preview']}>
      <PreviewPage />
    </MemoryRouter>,
  )
}

describe('PreviewPage', () => {
  it('renders without errors when no active session', () => {
    renderPage()
    expect(screen.getByTestId('preview-page')).toBeDefined()
    expect(screen.getByText('Preview')).toBeDefined()
  })

  it('shows no-project message when no project is selected', () => {
    renderPage()
    expect(screen.getByTestId('no-project-message')).toBeDefined()
    expect(screen.getByText('Select a project to preview.')).toBeDefined()
  })

  it('shows no-session state with start button when project selected', () => {
    useProjectStore.setState({ selectedProjectId: 'proj-1' })
    renderPage()
    expect(screen.getByTestId('no-session')).toBeDefined()
    expect(screen.getByTestId('start-preview-btn')).toBeDefined()
  })

  it('shows initializing status', () => {
    useProjectStore.setState({ selectedProjectId: 'proj-1' })
    usePreviewStore.setState({ status: 'initializing' })
    renderPage()
    expect(screen.getByTestId('status-initializing')).toBeDefined()
  })

  it('shows generating status with progress bar', () => {
    useProjectStore.setState({ selectedProjectId: 'proj-1' })
    usePreviewStore.setState({ sessionId: 'sess-1', status: 'generating', progress: 0.5 })
    renderPage()
    expect(screen.getByTestId('status-generating')).toBeDefined()
    expect(screen.getByTestId('progress-bar')).toBeDefined()
    expect(screen.getByText('50%')).toBeDefined()
  })

  it('shows player placeholder when ready', () => {
    useProjectStore.setState({ selectedProjectId: 'proj-1' })
    usePreviewStore.setState({ sessionId: 'sess-1', status: 'ready' })
    renderPage()
    expect(screen.getByTestId('player-placeholder')).toBeDefined()
  })

  it('shows error message with retry button', () => {
    useProjectStore.setState({ selectedProjectId: 'proj-1' })
    usePreviewStore.setState({ sessionId: null, status: 'error', error: 'Something failed' })
    renderPage()
    expect(screen.getByTestId('error-message')).toBeDefined()
    expect(screen.getByText('Preview error: Something failed')).toBeDefined()
    expect(screen.getByTestId('retry-preview-btn')).toBeDefined()
  })

  it('shows expired status with restart button', () => {
    useProjectStore.setState({ selectedProjectId: 'proj-1' })
    usePreviewStore.setState({ sessionId: null, status: 'expired' })
    renderPage()
    expect(screen.getByTestId('status-expired')).toBeDefined()
    expect(screen.getByTestId('restart-preview-btn')).toBeDefined()
  })

  it('attempts to connect when project is selected and no session', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ session_id: 'sess-auto' }), { status: 202 }),
    )

    useProjectStore.setState({ selectedProjectId: 'proj-1' })
    renderPage()

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        '/api/v1/projects/proj-1/preview/start',
        expect.objectContaining({ method: 'POST' }),
      )
    })
  })
})
