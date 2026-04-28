import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import ThemeSelector from '../ThemeSelector'
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

describe('ThemeSelector', () => {
  it('renders three theme options', () => {
    render(<ThemeSelector />)
    expect(screen.getByTestId('theme-option-light')).toBeDefined()
    expect(screen.getByTestId('theme-option-dark')).toBeDefined()
    expect(screen.getByTestId('theme-option-system')).toBeDefined()
  })

  it('marks the current theme as pressed', () => {
    useSettingsStore.setState({ theme: 'light' })
    render(<ThemeSelector />)
    expect(screen.getByTestId('theme-option-light').getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByTestId('theme-option-dark').getAttribute('aria-pressed')).toBe('false')
  })

  it('dispatches setTheme when an option is clicked and updates DOM', () => {
    render(<ThemeSelector />)
    fireEvent.click(screen.getByTestId('theme-option-dark'))
    expect(useSettingsStore.getState().theme).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')

    fireEvent.click(screen.getByTestId('theme-option-light'))
    expect(useSettingsStore.getState().theme).toBe('light')
    expect(document.documentElement.dataset.theme).toBe('light')
  })

  it('exposes the group label for assistive tech', () => {
    render(<ThemeSelector />)
    const group = screen.getByRole('group', { name: 'Theme' })
    expect(group).toBeDefined()
  })
})
