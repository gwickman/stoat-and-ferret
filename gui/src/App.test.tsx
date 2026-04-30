import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
import { DEFAULT_PANEL_SIZES, DEFAULT_PANEL_VISIBILITY, useWorkspaceStore } from './stores/workspaceStore'

class MockWebSocket {
  static readonly OPEN = 1
  onopen: (() => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  onmessage: ((e: MessageEvent) => void) | null = null
  readyState = MockWebSocket.OPEN
  close() {}
  send() {}
}

beforeEach(() => {
  window.localStorage.clear()
  useWorkspaceStore.setState({
    preset: 'edit',
    anchorPreset: 'edit',
    panelSizes: { ...DEFAULT_PANEL_SIZES },
    panelVisibility: { ...DEFAULT_PANEL_VISIBILITY },
    sizesByPreset: {},
  })
  vi.stubGlobal('WebSocket', MockWebSocket)
  vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('no-fetch'))
})

describe('App', () => {
  it('renders the shell layout', () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('status-bar')).toBeDefined()
  })

  it('renders preview page in preview panel in default state (BL-306 per-panel routing)', () => {
    // Default state: edit preset, only preview visible.
    // WorkspaceLayout renders PreviewPage in preview panel via PRESETS.edit.routes.preview.
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('preview-page')).toBeDefined()
  })

  it('renders library page in library panel when edit preset is fully active', () => {
    // Apply edit preset so library, timeline, effects, preview panels are all visible.
    useWorkspaceStore.getState().setPreset('edit')
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )
    // LibraryPage heading is rendered inside the library panel.
    expect(screen.getByRole('heading', { name: 'Library' })).toBeDefined()
  })
})
