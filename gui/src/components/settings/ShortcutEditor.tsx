import { useState } from 'react'
import { useSettings } from '../../hooks/useSettings'

interface RowState {
  /** Current draft value in the input field. */
  draft: string
  /** Whether the user has typed in this field (drives input value source). */
  touched: boolean
  /** Validation/save error message, if any. */
  error: string | null
}

const ACTION_LABELS: Record<string, string> = {
  'workspace.preset.edit': 'Workspace: Edit preset',
  'workspace.preset.review': 'Workspace: Review preset',
  'workspace.preset.render': 'Workspace: Render preset',
  'settings.toggle': 'Toggle settings panel',
}

/**
 * Editor that lists every registered shortcut and lets the user rebind each
 * one. Validation (empty / browser-reserved combos) runs in the store; the
 * editor surfaces the resulting error message inline next to the row.
 */
export default function ShortcutEditor() {
  const { shortcuts, updateShortcut } = useSettings()
  const [rows, setRows] = useState<Record<string, RowState>>({})

  const getRow = (action: string): RowState =>
    rows[action] ?? { draft: shortcuts[action] ?? '', touched: false, error: null }

  const handleDraftChange = (action: string, value: string) => {
    setRows((prev) => ({
      ...prev,
      [action]: { draft: value, touched: true, error: null },
    }))
  }

  const handleSave = (action: string) => {
    const row = getRow(action)
    try {
      updateShortcut(action, row.draft)
      setRows((prev) => ({
        ...prev,
        [action]: { draft: row.draft, touched: true, error: null },
      }))
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Invalid shortcut'
      setRows((prev) => ({
        ...prev,
        [action]: { draft: row.draft, touched: true, error: message },
      }))
    }
  }

  const actions = Object.keys(shortcuts).sort()

  return (
    <div data-testid="shortcut-editor" className="space-y-3">
      {actions.map((action) => {
        const row = getRow(action)
        const inputId = `shortcut-input-${action}`
        const errorId = `shortcut-error-${action}`
        return (
          <div
            key={action}
            data-testid={`shortcut-row-${action}`}
            className="flex flex-col gap-1"
          >
            <div className="flex items-center gap-3">
              <label
                htmlFor={inputId}
                className="flex-1 text-sm text-gray-300"
              >
                {ACTION_LABELS[action] ?? action}
              </label>
              <input
                id={inputId}
                type="text"
                value={row.touched ? row.draft : shortcuts[action]}
                onChange={(e) => handleDraftChange(action, e.target.value)}
                aria-invalid={row.error ? true : undefined}
                aria-describedby={row.error ? errorId : undefined}
                data-testid={`shortcut-input-${action}`}
                className="w-32 rounded border border-gray-700 bg-gray-900 px-2 py-1 font-mono text-sm text-gray-100 focus:border-blue-500 focus:outline-none"
              />
              <button
                type="button"
                onClick={() => handleSave(action)}
                data-testid={`shortcut-save-${action}`}
                className="rounded border border-gray-600 bg-gray-800 px-2 py-1 text-xs text-gray-200 hover:bg-gray-700"
              >
                Save
              </button>
            </div>
            {row.error && (
              <p
                id={errorId}
                role="alert"
                data-testid={`shortcut-error-${action}`}
                className="text-xs text-red-400"
              >
                {row.error}
              </p>
            )}
          </div>
        )
      })}
    </div>
  )
}
