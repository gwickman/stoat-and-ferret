import { renderHook, act } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { useSettings } from '../useSettings'
import { DEFAULT_SHORTCUTS, useSettingsStore } from '../../stores/settingsStore'

beforeEach(() => {
  window.localStorage.clear()
  useSettingsStore.setState({
    theme: 'system',
    shortcuts: { ...DEFAULT_SHORTCUTS },
  })
  delete document.documentElement.dataset.theme
})

afterEach(() => {
  window.localStorage.clear()
})

describe('useSettings', () => {
  it('exposes current theme and shortcuts', () => {
    const { result } = renderHook(() => useSettings())
    expect(result.current.theme).toBe('system')
    expect(result.current.shortcuts).toEqual(DEFAULT_SHORTCUTS)
  })

  it('updates theme through setTheme and reflects new value on next render', () => {
    const { result } = renderHook(() => useSettings())
    act(() => {
      result.current.setTheme('light')
    })
    expect(result.current.theme).toBe('light')
    expect(document.documentElement.dataset.theme).toBe('light')
  })

  it('updates shortcuts through updateShortcut', () => {
    const { result } = renderHook(() => useSettings())
    act(() => {
      result.current.updateShortcut('workspace.preset.edit', 'Ctrl+!')
    })
    expect(result.current.shortcuts['workspace.preset.edit']).toBe('Ctrl+!')
  })

  it('resets to defaults via resetDefaults', () => {
    const { result } = renderHook(() => useSettings())
    act(() => {
      result.current.setTheme('dark')
      result.current.updateShortcut('workspace.preset.edit', 'Ctrl+!')
    })
    act(() => {
      result.current.resetDefaults()
    })
    expect(result.current.theme).toBe('system')
    expect(result.current.shortcuts).toEqual(DEFAULT_SHORTCUTS)
  })
})
