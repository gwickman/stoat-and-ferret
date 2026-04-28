import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import WorkspacePresetSelector from '../WorkspacePresetSelector'
import {
  DEFAULT_PANEL_SIZES,
  DEFAULT_PANEL_VISIBILITY,
  useWorkspaceStore,
} from '../../../stores/workspaceStore'

beforeEach(() => {
  window.localStorage.clear()
  useWorkspaceStore.setState({
    preset: 'edit',
    panelSizes: { ...DEFAULT_PANEL_SIZES },
    panelVisibility: { ...DEFAULT_PANEL_VISIBILITY },
  })
})

afterEach(() => {
  window.localStorage.clear()
})

describe('WorkspacePresetSelector', () => {
  it('renders all four preset options', () => {
    render(<WorkspacePresetSelector />)
    const select = screen.getByTestId('workspace-preset-selector') as HTMLSelectElement
    const values = Array.from(select.options).map((option) => option.value)
    expect(values).toEqual(['edit', 'review', 'render', 'custom'])
  })

  it('reflects the current preset from workspaceStore', () => {
    useWorkspaceStore.setState({ preset: 'render' })
    render(<WorkspacePresetSelector />)
    const select = screen.getByTestId('workspace-preset-selector') as HTMLSelectElement
    expect(select.value).toBe('render')
  })

  it('dispatches setPreset on change', () => {
    render(<WorkspacePresetSelector />)
    const select = screen.getByTestId('workspace-preset-selector') as HTMLSelectElement
    fireEvent.change(select, { target: { value: 'review' } })
    expect(useWorkspaceStore.getState().preset).toBe('review')
  })
})
