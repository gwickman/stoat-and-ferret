import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  DEFAULT_SHORTCUTS,
  SETTINGS_SHORTCUTS_STORAGE_KEY,
  SETTINGS_THEME_STORAGE_KEY,
  _isReservedCombo,
  useSettingsStore,
} from '../settingsStore'

function resetStore() {
  useSettingsStore.setState({
    theme: 'system',
    shortcuts: { ...DEFAULT_SHORTCUTS },
  })
}

beforeEach(() => {
  window.localStorage.clear()
  resetStore()
  delete document.documentElement.dataset.theme
  vi.restoreAllMocks()
})

afterEach(() => {
  window.localStorage.clear()
})

describe('settingsStore', () => {
  it('initializes with defaults when localStorage is empty', () => {
    const state = useSettingsStore.getState()
    expect(state.theme).toBe('system')
    expect(state.shortcuts).toEqual(DEFAULT_SHORTCUTS)
  })

  describe('setTheme', () => {
    it('applies valid theme values and writes data-theme attribute', () => {
      useSettingsStore.getState().setTheme('light')
      expect(useSettingsStore.getState().theme).toBe('light')
      expect(document.documentElement.dataset.theme).toBe('light')

      useSettingsStore.getState().setTheme('dark')
      expect(useSettingsStore.getState().theme).toBe('dark')
      expect(document.documentElement.dataset.theme).toBe('dark')

      useSettingsStore.getState().setTheme('system')
      expect(useSettingsStore.getState().theme).toBe('system')
      expect(document.documentElement.dataset.theme).toBe('system')
    })

    it('persists theme to localStorage', () => {
      useSettingsStore.getState().setTheme('light')
      expect(window.localStorage.getItem(SETTINGS_THEME_STORAGE_KEY)).toBe('"light"')
    })

    it('throws TypeError on invalid theme values (INV-001)', () => {
      expect(() =>
        // @ts-expect-error -- testing runtime guard
        useSettingsStore.getState().setTheme('mauve'),
      ).toThrow(TypeError)
      expect(useSettingsStore.getState().theme).toBe('system')
    })

    it('throws TypeError on null/undefined theme', () => {
      expect(() =>
        // @ts-expect-error -- testing runtime guard
        useSettingsStore.getState().setTheme(null),
      ).toThrow(TypeError)
      expect(() =>
        // @ts-expect-error -- testing runtime guard
        useSettingsStore.getState().setTheme(undefined),
      ).toThrow(TypeError)
    })
  })

  describe('updateShortcut', () => {
    it('updates registered actions with valid combos', () => {
      useSettingsStore.getState().updateShortcut('workspace.preset.edit', 'Ctrl+!')
      expect(useSettingsStore.getState().shortcuts['workspace.preset.edit']).toBe('Ctrl+!')
    })

    it('persists shortcut updates to localStorage', () => {
      useSettingsStore.getState().updateShortcut('workspace.preset.edit', 'Ctrl+!')
      const persisted = JSON.parse(
        window.localStorage.getItem(SETTINGS_SHORTCUTS_STORAGE_KEY) ?? '{}',
      )
      expect(persisted['workspace.preset.edit']).toBe('Ctrl+!')
    })

    it('throws RangeError when action is not registered', () => {
      expect(() =>
        useSettingsStore.getState().updateShortcut('not.an.action', 'Ctrl+P'),
      ).toThrow(RangeError)
    })

    it('rejects empty combo with Error', () => {
      expect(() =>
        useSettingsStore.getState().updateShortcut('workspace.preset.edit', ''),
      ).toThrow(/non-empty/)
      expect(() =>
        useSettingsStore.getState().updateShortcut('workspace.preset.edit', '   '),
      ).toThrow(/non-empty/)
    })

    it('rejects browser-reserved combos with Error', () => {
      expect(() =>
        useSettingsStore.getState().updateShortcut('workspace.preset.edit', 'Ctrl+R'),
      ).toThrow(/browser-reserved/)
      expect(() =>
        useSettingsStore.getState().updateShortcut('workspace.preset.edit', 'F5'),
      ).toThrow(/browser-reserved/)
      expect(() =>
        useSettingsStore.getState().updateShortcut('workspace.preset.edit', 'F12'),
      ).toThrow(/browser-reserved/)
    })

    it('does not mutate state on validation failure', () => {
      const before = { ...useSettingsStore.getState().shortcuts }
      expect(() =>
        useSettingsStore.getState().updateShortcut('workspace.preset.edit', 'F5'),
      ).toThrow()
      expect(useSettingsStore.getState().shortcuts).toEqual(before)
    })
  })

  describe('resetDefaults', () => {
    it('restores theme=system and default shortcuts and clears localStorage', () => {
      useSettingsStore.getState().setTheme('light')
      useSettingsStore.getState().updateShortcut('workspace.preset.edit', 'Ctrl+!')
      expect(window.localStorage.getItem(SETTINGS_THEME_STORAGE_KEY)).not.toBeNull()
      expect(window.localStorage.getItem(SETTINGS_SHORTCUTS_STORAGE_KEY)).not.toBeNull()

      useSettingsStore.getState().resetDefaults()
      const state = useSettingsStore.getState()
      expect(state.theme).toBe('system')
      expect(state.shortcuts).toEqual(DEFAULT_SHORTCUTS)
      expect(document.documentElement.dataset.theme).toBe('system')
      expect(window.localStorage.getItem(SETTINGS_THEME_STORAGE_KEY)).toBeNull()
      expect(window.localStorage.getItem(SETTINGS_SHORTCUTS_STORAGE_KEY)).toBeNull()
    })
  })

  describe('persistence and hydration', () => {
    it('falls back to defaults on malformed JSON (AC-5)', async () => {
      window.localStorage.setItem(SETTINGS_THEME_STORAGE_KEY, 'not-json{')
      window.localStorage.setItem(SETTINGS_SHORTCUTS_STORAGE_KEY, 'not-json{')
      vi.resetModules()
      const mod = await import('../settingsStore')
      const state = mod.useSettingsStore.getState()
      expect(state.theme).toBe('system')
      expect(state.shortcuts).toEqual(DEFAULT_SHORTCUTS)
    })

    it('discards unknown action keys when hydrating shortcuts', async () => {
      window.localStorage.setItem(
        SETTINGS_SHORTCUTS_STORAGE_KEY,
        JSON.stringify({
          'workspace.preset.edit': 'Ctrl+!',
          'unknown.action': 'Ctrl+Z',
        }),
      )
      vi.resetModules()
      const mod = await import('../settingsStore')
      const state = mod.useSettingsStore.getState()
      expect(state.shortcuts['workspace.preset.edit']).toBe('Ctrl+!')
      expect(state.shortcuts['unknown.action']).toBeUndefined()
    })

    it('restores valid persisted theme', async () => {
      window.localStorage.setItem(SETTINGS_THEME_STORAGE_KEY, JSON.stringify('light'))
      vi.resetModules()
      const mod = await import('../settingsStore')
      const state = mod.useSettingsStore.getState()
      expect(state.theme).toBe('light')
    })

    it('falls back to system when persisted theme is invalid', async () => {
      window.localStorage.setItem(SETTINGS_THEME_STORAGE_KEY, JSON.stringify('plaid'))
      vi.resetModules()
      const mod = await import('../settingsStore')
      expect(mod.useSettingsStore.getState().theme).toBe('system')
    })

    it('applies theme to data-theme attribute on first load', async () => {
      window.localStorage.setItem(SETTINGS_THEME_STORAGE_KEY, JSON.stringify('dark'))
      delete document.documentElement.dataset.theme
      vi.resetModules()
      await import('../settingsStore')
      expect(document.documentElement.dataset.theme).toBe('dark')
    })
  })

  describe('_isReservedCombo helper', () => {
    it('flags reserved keys regardless of casing or modifier order', () => {
      expect(_isReservedCombo('Ctrl+R')).toBe(true)
      expect(_isReservedCombo('ctrl+r')).toBe(true)
      expect(_isReservedCombo('R+Ctrl')).toBe(true)
      expect(_isReservedCombo('F5')).toBe(true)
      expect(_isReservedCombo('f12')).toBe(true)
    })

    it('does not flag custom combos', () => {
      expect(_isReservedCombo('Ctrl+1')).toBe(false)
      expect(_isReservedCombo('Ctrl+,')).toBe(false)
      expect(_isReservedCombo('Ctrl+Shift+P')).toBe(false)
    })
  })
})
