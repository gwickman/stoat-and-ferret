import { useState } from 'react'
import type { AppliedEffect } from '../stores/effectStackStore'
import { highlightFilter } from './FilterPreview'

interface EffectStackProps {
  effects: AppliedEffect[]
  isLoading: boolean
  onEdit: (index: number, effect: AppliedEffect) => void
  onRemove: (index: number) => void
}

/** Renders the ordered list of effects applied to a clip with edit/remove actions. */
export default function EffectStack({ effects, isLoading, onEdit, onRemove }: EffectStackProps) {
  const [confirmIndex, setConfirmIndex] = useState<number | null>(null)

  if (isLoading) {
    return (
      <div data-testid="effect-stack-loading" className="rounded border border-gray-700 p-4">
        <p className="text-sm text-gray-400">Loading effects...</p>
      </div>
    )
  }

  if (effects.length === 0) {
    return (
      <div data-testid="effect-stack-empty" className="rounded border border-gray-700 p-4">
        <p className="text-sm text-gray-400">No effects applied to this clip.</p>
      </div>
    )
  }

  return (
    <div data-testid="effect-stack" className="mt-4">
      <h3 className="mb-2 text-lg font-semibold text-white">Effect Stack</h3>
      <ol className="space-y-2">
        {effects.map((effect, index) => {
          const paramSummary = Object.entries(effect.parameters)
            .slice(0, 3)
            .map(([k, v]) => `${k}: ${String(v)}`)
            .join(', ')

          return (
            <li
              key={index}
              data-testid={`effect-entry-${index}`}
              className="rounded border border-gray-700 bg-gray-800 p-3"
            >
              <div className="flex items-center justify-between">
                <div>
                  <span
                    className="font-medium text-white"
                    data-testid={`effect-type-${index}`}
                  >
                    {effect.effect_type}
                  </span>
                  {paramSummary && (
                    <span
                      className="ml-2 text-xs text-gray-400"
                      data-testid={`effect-params-${index}`}
                    >
                      ({paramSummary})
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    data-testid={`edit-effect-${index}`}
                    onClick={() => onEdit(index, effect)}
                    className="rounded bg-gray-700 px-2 py-1 text-xs text-gray-300 hover:bg-gray-600"
                  >
                    Edit
                  </button>
                  {confirmIndex === index ? (
                    <div className="flex gap-1" data-testid={`confirm-delete-${index}`}>
                      <button
                        type="button"
                        data-testid={`confirm-yes-${index}`}
                        onClick={() => {
                          onRemove(index)
                          setConfirmIndex(null)
                        }}
                        className="rounded bg-red-700 px-2 py-1 text-xs text-white hover:bg-red-600"
                      >
                        Confirm
                      </button>
                      <button
                        type="button"
                        data-testid={`confirm-no-${index}`}
                        onClick={() => setConfirmIndex(null)}
                        className="rounded bg-gray-700 px-2 py-1 text-xs text-gray-300 hover:bg-gray-600"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      data-testid={`remove-effect-${index}`}
                      onClick={() => setConfirmIndex(index)}
                      className="rounded bg-gray-700 px-2 py-1 text-xs text-red-400 hover:bg-gray-600"
                    >
                      Remove
                    </button>
                  )}
                </div>
              </div>
              <pre
                className="mt-2 overflow-x-auto text-xs text-gray-400"
                data-testid={`effect-filter-${index}`}
              >
                {highlightFilter(effect.filter_string)}
              </pre>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
