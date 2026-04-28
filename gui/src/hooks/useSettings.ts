import { useSettingsStore } from '../stores/settingsStore'
import type { Theme, ShortcutMap } from '../stores/settingsStore'

/**
 * Component-level access hook for settingsStore.
 *
 * Returns current theme and shortcut map plus the action methods for
 * mutating them. Intended for use inside React components — non-React
 * modules should import the store directly via `useSettingsStore`.
 */
export function useSettings() {
  const theme = useSettingsStore((s) => s.theme)
  const shortcuts = useSettingsStore((s) => s.shortcuts)
  const setTheme = useSettingsStore((s) => s.setTheme)
  const updateShortcut = useSettingsStore((s) => s.updateShortcut)
  const resetDefaults = useSettingsStore((s) => s.resetDefaults)

  return {
    theme,
    shortcuts,
    setTheme,
    updateShortcut,
    resetDefaults,
  }
}

export type { Theme, ShortcutMap }
