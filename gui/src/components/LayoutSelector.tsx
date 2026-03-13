import type { LayoutPreset } from '../types/timeline'
import { useComposeStore } from '../stores/composeStore'

/** Displays all layout presets as selectable items. */
export default function LayoutSelector() {
  const presets = useComposeStore((s) => s.presets)
  const selectedPreset = useComposeStore((s) => s.selectedPreset)
  const selectPreset = useComposeStore((s) => s.selectPreset)

  if (presets.length === 0) return null

  return (
    <div data-testid="layout-selector">
      <h4 className="mb-2 text-sm font-medium text-gray-300">Layout Presets</h4>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
        {presets.map((preset: LayoutPreset) => (
          <button
            key={preset.name}
            data-testid={`preset-${preset.name}`}
            className={`rounded border px-3 py-2 text-left text-sm transition-colors ${
              selectedPreset === preset.name
                ? 'border-blue-500 bg-blue-900/30 text-white'
                : 'border-gray-700 bg-gray-800 text-gray-300 hover:border-gray-500'
            }`}
            onClick={() => selectPreset(preset.name)}
            title={preset.description}
          >
            <span className="block font-medium">{preset.name}</span>
            <span className="block text-xs text-gray-400">{preset.description}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
