import { useEffect } from 'react'
import ShortcutEditor from './ShortcutEditor'
import ThemeSelector from './ThemeSelector'

interface SettingsPanelProps {
  /** Whether the panel is currently visible. */
  open: boolean
  /** Callback invoked when the user dismisses the panel. */
  onClose: () => void
}

/**
 * Modal settings panel. Hosts ThemeSelector and ShortcutEditor sections.
 *
 * Dismissed via the close button or by pressing Escape while the panel is
 * open. Mounted at z-50 over the workspace so it does not interfere with
 * panel resize chrome.
 */
export default function SettingsPanel({ open, onClose }: SettingsPanelProps) {
  useEffect(() => {
    if (!open) return
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => {
      window.removeEventListener('keydown', handleKey)
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      data-testid="settings-panel"
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-panel-title"
    >
      <div className="w-full max-w-xl rounded-lg border border-gray-700 bg-gray-800 p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2
            id="settings-panel-title"
            className="text-lg font-semibold text-gray-100"
          >
            Settings
          </h2>
          <button
            type="button"
            onClick={onClose}
            data-testid="settings-panel-close"
            aria-label="Close settings"
            className="rounded border border-gray-600 px-2 py-1 text-sm text-gray-300 hover:bg-gray-700"
          >
            Close
          </button>
        </div>

        <section className="mb-6" aria-labelledby="settings-theme-heading">
          <h3
            id="settings-theme-heading"
            className="mb-2 text-sm font-medium text-gray-300"
          >
            Theme
          </h3>
          <ThemeSelector />
        </section>

        <section aria-labelledby="settings-shortcuts-heading">
          <h3
            id="settings-shortcuts-heading"
            className="mb-2 text-sm font-medium text-gray-300"
          >
            Keyboard Shortcuts
          </h3>
          <ShortcutEditor />
        </section>
      </div>
    </div>
  )
}
