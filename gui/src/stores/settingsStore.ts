import { create } from 'zustand'

/** Theme identifiers supported by the settings store. */
export type Theme = 'light' | 'dark' | 'system'

/** Map of action key → key combo string. */
export type ShortcutMap = Record<string, string>

const THEME_STORAGE_KEY = 'stoat-theme'
const SHORTCUTS_STORAGE_KEY = 'stoat-shortcuts'

const VALID_THEMES: ReadonlySet<Theme> = new Set(['light', 'dark', 'system'])

/**
 * Default keyboard shortcut bindings. Action keys here are the canonical
 * registry — `updateShortcut` rejects actions not present in this map.
 *
 * Keep this list in sync with the bindings registered in Shell.tsx and
 * elsewhere via `useKeyboardShortcuts`.
 */
export const DEFAULT_SHORTCUTS: ShortcutMap = {
  'workspace.preset.edit': 'Ctrl+1',
  'workspace.preset.review': 'Ctrl+2',
  'workspace.preset.render': 'Ctrl+3',
  'settings.toggle': 'Ctrl+,',
}

/**
 * Browser-reserved combos that must not be rebound. Compared
 * case-insensitively after normalizing modifier order.
 */
const RESERVED_COMBOS: ReadonlySet<string> = new Set([
  'f5',
  'f11',
  'f12',
  'ctrl+r',
  'ctrl+t',
  'ctrl+w',
  'ctrl+n',
  'ctrl+l',
  'ctrl+shift+t',
  'ctrl+shift+n',
  'ctrl+shift+w',
])

export interface SettingsState {
  theme: Theme
  shortcuts: ShortcutMap
}

export interface SettingsStore extends SettingsState {
  setTheme: (theme: Theme) => void
  updateShortcut: (action: string, combo: string) => void
  resetDefaults: () => void
}

function normalizeCombo(combo: string): string {
  const parts = combo
    .split('+')
    .map((p) => p.trim().toLowerCase())
    .filter((p) => p.length > 0)
  if (parts.length === 0) return ''
  const order: Record<string, number> = { ctrl: 0, meta: 0, alt: 1, shift: 2 }
  const modifiers = parts
    .filter((p) => p in order || p === 'control' || p === 'cmd' || p === 'option')
    .map((p) => {
      if (p === 'control' || p === 'cmd') return 'ctrl'
      if (p === 'option') return 'alt'
      return p
    })
    .sort((a, b) => (order[a] ?? 99) - (order[b] ?? 99))
  const key = parts.find(
    (p) =>
      !(p in order) &&
      p !== 'control' &&
      p !== 'cmd' &&
      p !== 'option' &&
      p !== 'meta',
  )
  if (!key) return modifiers.join('+')
  return [...new Set(modifiers), key].join('+')
}

function isReserved(combo: string): boolean {
  return RESERVED_COMBOS.has(normalizeCombo(combo))
}

/** Apply the theme value to `<html data-theme>` so CSS rules can react. */
export function applyThemeToDocument(theme: Theme): void {
  if (typeof document === 'undefined') return
  document.documentElement.dataset.theme = theme
}

function loadTheme(): Theme {
  if (typeof window === 'undefined') return 'system'
  try {
    const raw = window.localStorage.getItem(THEME_STORAGE_KEY)
    if (!raw) return 'system'
    const parsed: unknown = JSON.parse(raw)
    if (typeof parsed === 'string' && VALID_THEMES.has(parsed as Theme)) {
      return parsed as Theme
    }
    return 'system'
  } catch {
    return 'system'
  }
}

function loadShortcuts(): ShortcutMap {
  if (typeof window === 'undefined') return { ...DEFAULT_SHORTCUTS }
  try {
    const raw = window.localStorage.getItem(SHORTCUTS_STORAGE_KEY)
    if (!raw) return { ...DEFAULT_SHORTCUTS }
    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return { ...DEFAULT_SHORTCUTS }
    const merged: ShortcutMap = { ...DEFAULT_SHORTCUTS }
    for (const [action, combo] of Object.entries(parsed as Record<string, unknown>)) {
      if (action in DEFAULT_SHORTCUTS && typeof combo === 'string' && combo.length > 0) {
        merged[action] = combo
      }
    }
    return merged
  } catch {
    return { ...DEFAULT_SHORTCUTS }
  }
}

function saveTheme(theme: Theme): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, JSON.stringify(theme))
  } catch {
    // localStorage unavailable — silently degrade.
  }
}

function saveShortcuts(shortcuts: ShortcutMap): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(SHORTCUTS_STORAGE_KEY, JSON.stringify(shortcuts))
  } catch {
    // localStorage unavailable — silently degrade.
  }
}

function clearSettingsStorage(): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.removeItem(THEME_STORAGE_KEY)
    window.localStorage.removeItem(SHORTCUTS_STORAGE_KEY)
  } catch {
    // localStorage unavailable — silently degrade.
  }
}

export const useSettingsStore = create<SettingsStore>((set, get) => {
  const theme = loadTheme()
  const shortcuts = loadShortcuts()
  applyThemeToDocument(theme)
  return {
    theme,
    shortcuts,
    setTheme: (next) => {
      if (typeof next !== 'string' || !VALID_THEMES.has(next)) {
        throw new TypeError(`setTheme: invalid theme "${String(next)}"`)
      }
      applyThemeToDocument(next)
      set({ theme: next })
      saveTheme(next)
    },
    updateShortcut: (action, combo) => {
      if (typeof action !== 'string' || !(action in get().shortcuts)) {
        throw new RangeError(`updateShortcut: action "${String(action)}" is not registered`)
      }
      if (typeof combo !== 'string' || combo.trim().length === 0) {
        throw new Error('updateShortcut: combo must be a non-empty string')
      }
      if (isReserved(combo)) {
        throw new Error(
          `updateShortcut: combo "${combo}" conflicts with a browser-reserved key`,
        )
      }
      set((state) => ({ shortcuts: { ...state.shortcuts, [action]: combo } }))
      saveShortcuts(get().shortcuts)
    },
    resetDefaults: () => {
      const defaults = { ...DEFAULT_SHORTCUTS }
      applyThemeToDocument('system')
      set({ theme: 'system', shortcuts: defaults })
      clearSettingsStorage()
    },
  }
})

/** Storage keys exposed for tests and external persistence consumers. */
export const SETTINGS_THEME_STORAGE_KEY = THEME_STORAGE_KEY
export const SETTINGS_SHORTCUTS_STORAGE_KEY = SHORTCUTS_STORAGE_KEY

/** @internal Test-only check that a combo would be flagged as reserved. */
export function _isReservedCombo(combo: string): boolean {
  return isReserved(combo)
}
