import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { useWorkspace } from '../useWorkspace'
import {
  DEFAULT_PANEL_SIZES,
  DEFAULT_PANEL_VISIBILITY,
  WORKSPACE_STORAGE_KEY,
  useWorkspaceStore,
} from '../../stores/workspaceStore'

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

describe('useWorkspace', () => {
  it('exposes current store state', () => {
    const { result } = renderHook(() => useWorkspace())
    expect(result.current.preset).toBe('edit')
    expect(result.current.panelSizes).toEqual(DEFAULT_PANEL_SIZES)
    expect(result.current.panelVisibility).toEqual(DEFAULT_PANEL_VISIBILITY)
  })

  it('triggers re-render when preset changes', () => {
    const { result } = renderHook(() => useWorkspace())
    act(() => {
      result.current.setPreset('review')
    })
    expect(result.current.preset).toBe('review')
  })

  it('reflects panel resize updates', () => {
    const { result } = renderHook(() => useWorkspace())
    act(() => {
      result.current.resizePanel('library', 33)
    })
    expect(result.current.panelSizes.library).toBe(33)
  })

  it('reflects panel visibility toggles', () => {
    const { result } = renderHook(() => useWorkspace())
    // First-run defaults: only `preview` is visible. Toggle reveals library.
    expect(result.current.panelVisibility.library).toBe(false)
    act(() => {
      result.current.togglePanel('library')
    })
    expect(result.current.panelVisibility.library).toBe(true)
  })

  it('resetLayout restores defaults via the hook', () => {
    const { result } = renderHook(() => useWorkspace())
    act(() => {
      // Resize via the hook to flip preset to custom and record an override.
      result.current.resizePanel('library', 5)
    })
    expect(result.current.preset).toBe('custom')
    expect(result.current.panelSizes.library).toBe(5)

    act(() => {
      result.current.resetLayout()
    })
    expect(result.current.preset).toBe('edit')
    expect(result.current.panelSizes).toEqual(DEFAULT_PANEL_SIZES)
    expect(window.localStorage.getItem(WORKSPACE_STORAGE_KEY)).toBeNull()
  })
})
