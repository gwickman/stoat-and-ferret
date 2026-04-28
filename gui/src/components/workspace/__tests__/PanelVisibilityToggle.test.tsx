import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import PanelVisibilityToggle from '../PanelVisibilityToggle'
import {
  DEFAULT_PANEL_SIZES,
  DEFAULT_PANEL_VISIBILITY,
  PANEL_IDS,
  WORKSPACE_STORAGE_KEY,
  useWorkspaceStore,
} from '../../../stores/workspaceStore'

beforeEach(() => {
  window.localStorage.clear()
  useWorkspaceStore.setState({
    preset: 'edit',
    anchorPreset: 'edit',
    panelSizes: { ...DEFAULT_PANEL_SIZES },
    panelVisibility: { ...DEFAULT_PANEL_VISIBILITY },
    sizesByPreset: {},
  })
})

afterEach(() => {
  window.localStorage.clear()
})

describe('PanelVisibilityToggle', () => {
  it('renders one toggle button per panel plus a reset button', () => {
    render(<PanelVisibilityToggle />)
    for (const panelId of PANEL_IDS) {
      expect(screen.getByTestId(`panel-toggle-${panelId}`)).toBeDefined()
    }
    expect(screen.getByTestId('panel-reset-layout')).toBeDefined()
  })

  it('reflects current visibility via aria-pressed', () => {
    render(<PanelVisibilityToggle />)
    // First-run defaults: only `preview` is visible.
    expect(screen.getByTestId('panel-toggle-preview').getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByTestId('panel-toggle-library').getAttribute('aria-pressed')).toBe('false')
  })

  it('toggles panel visibility on click', () => {
    render(<PanelVisibilityToggle />)
    fireEvent.click(screen.getByTestId('panel-toggle-library'))
    expect(useWorkspaceStore.getState().panelVisibility.library).toBe(true)
    fireEvent.click(screen.getByTestId('panel-toggle-library'))
    expect(useWorkspaceStore.getState().panelVisibility.library).toBe(false)
  })

  it('reset button restores defaults and clears localStorage', () => {
    useWorkspaceStore.getState().togglePanel('library')
    useWorkspaceStore.getState().resizePanel('preview', 5)
    expect(window.localStorage.getItem(WORKSPACE_STORAGE_KEY)).not.toBeNull()

    render(<PanelVisibilityToggle />)
    fireEvent.click(screen.getByTestId('panel-reset-layout'))

    const state = useWorkspaceStore.getState()
    expect(state.panelVisibility).toEqual(DEFAULT_PANEL_VISIBILITY)
    expect(state.panelSizes).toEqual(DEFAULT_PANEL_SIZES)
    expect(window.localStorage.getItem(WORKSPACE_STORAGE_KEY)).toBeNull()
  })
})
