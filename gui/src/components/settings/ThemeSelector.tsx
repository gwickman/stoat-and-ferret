import { useSettings } from '../../hooks/useSettings'
import type { Theme } from '../../stores/settingsStore'

const THEMES: ReadonlyArray<{ value: Theme; label: string }> = [
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
  { value: 'system', label: 'System' },
]

/**
 * Three-way toggle that drives `settingsStore.setTheme`.
 *
 * Renders a button group; the active theme button is visually distinguished
 * via `aria-pressed` and a contrast-bumped style. Selecting a theme applies
 * it immediately (the store writes `data-theme` on `<html>`).
 */
export default function ThemeSelector() {
  const { theme, setTheme } = useSettings()
  return (
    <fieldset
      aria-label="Theme"
      data-testid="theme-selector"
      className="m-0 flex min-w-0 items-center gap-2 border-0 p-0"
    >
      <legend className="sr-only">Theme</legend>
      {THEMES.map((option) => {
        const active = theme === option.value
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            data-testid={`theme-option-${option.value}`}
            onClick={() => setTheme(option.value)}
            className={
              active
                ? 'rounded border border-blue-500 bg-blue-600 px-3 py-1 text-sm text-white'
                : 'rounded border border-gray-600 bg-gray-800 px-3 py-1 text-sm text-gray-200 hover:bg-gray-700'
            }
          >
            {option.label}
          </button>
        )
      })}
    </fieldset>
  )
}
