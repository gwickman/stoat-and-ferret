import { useComposeStore } from '../stores/composeStore'
import type { LayoutPosition } from '../types/timeline'

/** Coordinate fields for custom position input. */
const COORD_FIELDS: (keyof LayoutPosition)[] = ['x', 'y', 'width', 'height']

/** Displays z-order layer stack and custom coordinate inputs. */
export default function LayerStack() {
  const positions = useComposeStore((s) => s.getActivePositions())
  const customPositions = useComposeStore((s) => s.customPositions)
  const updateCustomPosition = useComposeStore((s) => s.updateCustomPosition)

  /** Sorted layers by z_index descending (highest on top). */
  const sortedLayers = positions
    .map((pos, i) => ({ ...pos, index: i }))
    .sort((a, b) => b.z_index - a.z_index)

  return (
    <div data-testid="layer-stack">
      <h4 className="mb-2 text-sm font-medium text-gray-300">Layers</h4>
      {sortedLayers.length === 0 ? (
        <p className="text-sm text-gray-500">No layers to display</p>
      ) : (
        <ul className="space-y-1" data-testid="layer-list">
          {sortedLayers.map((layer) => (
            <li
              key={layer.index}
              data-testid={`layer-${layer.index}`}
              className="flex items-center justify-between rounded bg-gray-800 px-3 py-1.5 text-sm"
            >
              <span className="font-medium text-gray-200">Layer {layer.index + 1}</span>
              <span className="text-xs text-gray-400" data-testid={`layer-z-${layer.index}`}>
                z: {layer.z_index}
              </span>
            </li>
          ))}
        </ul>
      )}

      {customPositions.length > 0 && (
        <div className="mt-4" data-testid="custom-inputs">
          <h4 className="mb-2 text-sm font-medium text-gray-300">Custom Positions</h4>
          {customPositions.map((pos, i) => (
            <div key={i} className="mb-2 rounded bg-gray-800 p-2" data-testid={`custom-pos-${i}`}>
              <span className="mb-1 block text-xs font-medium text-gray-300">
                Position {i + 1}
              </span>
              <div className="grid grid-cols-4 gap-1">
                {COORD_FIELDS.map((field) => (
                  <label key={field} className="text-xs text-gray-400">
                    {field}
                    <input
                      type="number"
                      min={0}
                      max={1}
                      step={0.01}
                      value={pos[field]}
                      data-testid={`input-${i}-${field}`}
                      className="mt-0.5 block w-full rounded border border-gray-600 bg-gray-900 px-1.5 py-0.5 text-xs text-white"
                      onChange={(e) => {
                        const val = parseFloat(e.target.value)
                        if (!isNaN(val)) {
                          updateCustomPosition(i, field, val)
                        }
                      }}
                    />
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
