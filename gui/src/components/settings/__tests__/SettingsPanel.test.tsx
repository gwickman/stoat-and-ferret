import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import SettingsPanel from '../SettingsPanel'
import { DEFAULT_SHORTCUTS, useSettingsStore } from '../../../stores/settingsStore'

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

describe('SettingsPanel', () => {
  it('does not render when closed', () => {
    render(<SettingsPanel open={false} onClose={vi.fn()} />)
    expect(screen.queryByTestId('settings-panel')).toBeNull()
  })

  it('renders panel chrome and child sections when open', () => {
    render(<SettingsPanel open={true} onClose={vi.fn()} />)
    expect(screen.getByTestId('settings-panel')).toBeDefined()
    expect(screen.getByTestId('theme-selector')).toBeDefined()
    expect(screen.getByTestId('shortcut-editor')).toBeDefined()
  })

  it('exposes dialog role and labelled title', () => {
    render(<SettingsPanel open={true} onClose={vi.fn()} />)
    const dialog = screen.getByRole('dialog')
    expect(dialog.getAttribute('aria-modal')).toBe('true')
    expect(screen.getByRole('heading', { name: 'Settings' })).toBeDefined()
  })

  it('invokes onClose when close button is clicked', () => {
    const onClose = vi.fn()
    render(<SettingsPanel open={true} onClose={onClose} />)
    fireEvent.click(screen.getByTestId('settings-panel-close'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('invokes onClose when Escape is pressed while open', () => {
    const onClose = vi.fn()
    render(<SettingsPanel open={true} onClose={onClose} />)
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('does not listen for Escape when closed', () => {
    const onClose = vi.fn()
    render(<SettingsPanel open={false} onClose={onClose} />)
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).not.toHaveBeenCalled()
  })
})
