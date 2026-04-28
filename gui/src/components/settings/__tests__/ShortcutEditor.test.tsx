import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import ShortcutEditor from '../ShortcutEditor'
import { DEFAULT_SHORTCUTS, useSettingsStore } from '../../../stores/settingsStore'

beforeEach(() => {
  window.localStorage.clear()
  useSettingsStore.setState({
    theme: 'system',
    shortcuts: { ...DEFAULT_SHORTCUTS },
  })
})

afterEach(() => {
  window.localStorage.clear()
})

describe('ShortcutEditor', () => {
  it('renders one row per registered shortcut with current combo', () => {
    render(<ShortcutEditor />)
    for (const action of Object.keys(DEFAULT_SHORTCUTS)) {
      expect(screen.getByTestId(`shortcut-row-${action}`)).toBeDefined()
      const input = screen.getByTestId(`shortcut-input-${action}`) as HTMLInputElement
      expect(input.value).toBe(DEFAULT_SHORTCUTS[action])
    }
  })

  it('persists a valid rebind to the store', () => {
    render(<ShortcutEditor />)
    const input = screen.getByTestId('shortcut-input-workspace.preset.edit') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'Ctrl+!' } })
    fireEvent.click(screen.getByTestId('shortcut-save-workspace.preset.edit'))
    expect(useSettingsStore.getState().shortcuts['workspace.preset.edit']).toBe('Ctrl+!')
    expect(screen.queryByTestId('shortcut-error-workspace.preset.edit')).toBeNull()
  })

  it('shows inline error and rejects empty combo', () => {
    render(<ShortcutEditor />)
    const input = screen.getByTestId('shortcut-input-workspace.preset.edit') as HTMLInputElement
    fireEvent.change(input, { target: { value: '' } })
    fireEvent.click(screen.getByTestId('shortcut-save-workspace.preset.edit'))
    const error = screen.getByTestId('shortcut-error-workspace.preset.edit')
    expect(error.textContent).toMatch(/non-empty/)
    expect(useSettingsStore.getState().shortcuts['workspace.preset.edit']).toBe('Ctrl+1')
  })

  it('shows inline error and rejects browser-reserved combo (NFR-001)', () => {
    render(<ShortcutEditor />)
    const input = screen.getByTestId('shortcut-input-workspace.preset.edit') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'Ctrl+R' } })
    fireEvent.click(screen.getByTestId('shortcut-save-workspace.preset.edit'))
    const error = screen.getByTestId('shortcut-error-workspace.preset.edit')
    expect(error.textContent).toMatch(/browser-reserved/)
    expect(useSettingsStore.getState().shortcuts['workspace.preset.edit']).toBe('Ctrl+1')
  })

  it('clears any prior error on next valid save', () => {
    render(<ShortcutEditor />)
    const input = screen.getByTestId('shortcut-input-workspace.preset.edit') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'F5' } })
    fireEvent.click(screen.getByTestId('shortcut-save-workspace.preset.edit'))
    expect(screen.getByTestId('shortcut-error-workspace.preset.edit')).toBeDefined()

    fireEvent.change(input, { target: { value: 'Ctrl+!' } })
    fireEvent.click(screen.getByTestId('shortcut-save-workspace.preset.edit'))
    expect(screen.queryByTestId('shortcut-error-workspace.preset.edit')).toBeNull()
    expect(useSettingsStore.getState().shortcuts['workspace.preset.edit']).toBe('Ctrl+!')
  })
})
