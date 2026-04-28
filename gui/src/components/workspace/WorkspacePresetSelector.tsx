import { useWorkspace } from '../../hooks/useWorkspace'
import type { WorkspacePreset } from '../../stores/workspaceStore'

const PRESET_OPTIONS: { value: WorkspacePreset; label: string }[] = [
  { value: 'edit', label: 'Edit' },
  { value: 'review', label: 'Review' },
  { value: 'render', label: 'Render' },
  { value: 'custom', label: 'Custom' },
]

/**
 * Dropdown selector for workspace presets. Wired to workspaceStore.preset
 * so future preset definitions (BL-292) propagate from a single source.
 */
export default function WorkspacePresetSelector() {
  const { preset, setPreset } = useWorkspace()

  return (
    <label className="flex items-center gap-2 text-xs text-gray-400">
      <span className="sr-only">Workspace preset</span>
      <select
        value={preset}
        onChange={(event) => setPreset(event.target.value as WorkspacePreset)}
        className="rounded border border-gray-700 bg-gray-900 px-2 py-1 text-xs text-gray-200 focus:border-blue-500 focus:outline-none"
        data-testid="workspace-preset-selector"
        aria-label="Workspace preset"
      >
        {PRESET_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}
