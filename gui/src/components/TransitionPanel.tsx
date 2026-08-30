import { useCallback, useMemo, useState } from 'react'
import type { Clip } from '../generated/types'
import { useEffects } from '../hooks/useEffects'
import type { ParameterSchema } from '../stores/effectFormStore'
import { useEffectFormStore } from '../stores/effectFormStore'
import { useTransitionStore } from '../stores/transitionStore'
import ClipSelector from './ClipSelector'
import EffectParameterForm from './EffectParameterForm'

// Style names sent to POST /effects/transition (TransitionType.from_str() vocabulary)
const TRANSITION_STYLE_NAMES = ['fade', 'wipeleft', 'dissolve'] as const

interface TransitionPanelProps {
  readonly projectId: string
  readonly clips: Clip[]
}

/** Panel for applying transitions between adjacent clips. */
export default function TransitionPanel({ projectId, clips }: Readonly<TransitionPanelProps>) {
  const { effects } = useEffects()
  const sourceClipId = useTransitionStore((s) => s.sourceClipId)
  const targetClipId = useTransitionStore((s) => s.targetClipId)
  const selectSource = useTransitionStore((s) => s.selectSource)
  const selectTarget = useTransitionStore((s) => s.selectTarget)
  const resetTransition = useTransitionStore((s) => s.reset)
  const isReady = useTransitionStore((s) => s.isReady)

  const setSchema = useEffectFormStore((s) => s.setSchema)
  const resetForm = useEffectFormStore((s) => s.resetForm)
  const formParameters = useEffectFormStore((s) => s.parameters)

  const [selectedTransitionType, setSelectedTransitionType] = useState<string | null>(null)
  const [submitStatus, setSubmitStatus] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Map style names to parameter schemas via ai_hints.transition on registry effects
  const schemaByStyleName = useMemo(() => {
    const map: Record<string, ParameterSchema | undefined> = {}
    for (const e of effects) {
      const hint = (e.ai_hints as Record<string, unknown>)?.transition
      if (typeof hint === 'string' && e.parameter_schema) {
        map[hint] = e.parameter_schema as unknown as ParameterSchema
      }
    }
    return map
  }, [effects])

  const handleSelectPair = useCallback(
    (clipId: string, role: 'from' | 'to') => {
      if (role === 'from') {
        selectSource(clipId)
      } else {
        selectTarget(clipId)
      }
    },
    [selectSource, selectTarget],
  )

  const handleSelectStyle = useCallback(
    (styleName: string) => {
      setSelectedTransitionType(styleName)
      setSubmitStatus(null)
      const schema = schemaByStyleName[styleName]
      if (schema) {
        setSchema(schema)
      } else {
        resetForm()
      }
    },
    [schemaByStyleName, setSchema, resetForm],
  )

  const handleReset = useCallback(() => {
    resetTransition()
    setSelectedTransitionType(null)
    setSubmitStatus(null)
    resetForm()
  }, [resetTransition, resetForm])

  const handleSubmit = useCallback(async () => {
    if (!sourceClipId || !targetClipId || !selectedTransitionType) return
    setIsSubmitting(true)
    setSubmitStatus(null)

    try {
      const res = await fetch(`/api/v1/projects/${projectId}/effects/transition`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_clip_id: sourceClipId,
          target_clip_id: targetClipId,
          transition_type: selectedTransitionType,
          parameters: formParameters,
        }),
      })

      if (!res.ok) {
        const detail = await res.json().catch(() => null)
        const message = detail?.detail?.message || detail?.detail || res.statusText
        if (res.status === 400 && typeof message === 'string' && message.toLowerCase().includes('adjacent')) {
          setSubmitStatus('Error: Selected clips are not adjacent on the timeline.')
        } else {
          setSubmitStatus(`Error: ${message}`)
        }
        return
      }

      setSubmitStatus('Transition applied!')
      handleReset()
      setTimeout(() => setSubmitStatus(null), 2000)
    } catch (err) {
      setSubmitStatus(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setIsSubmitting(false)
    }
  }, [projectId, sourceClipId, targetClipId, selectedTransitionType, formParameters, handleReset])

  return (
    <div data-testid="transition-panel">
      {/* Clip pair selection */}
      <ClipSelector
        clips={clips}
        selectedClipId={null}
        onSelect={() => {}}
        pairMode
        selectedFromId={sourceClipId}
        selectedToId={targetClipId}
        onSelectPair={handleSelectPair}
      />

      {sourceClipId && targetClipId && (
        <button
          type="button"
          data-testid="reset-pair-btn"
          onClick={handleReset}
          className="mb-4 rounded bg-gray-700 px-3 py-1 text-sm text-gray-300 hover:bg-gray-600"
        >
          Reset Selection
        </button>
      )}

      {/* Transition type catalog */}
      <div data-testid="transition-catalog" className="mb-4">
        <h3 className="mb-2 text-lg font-semibold text-white">Transition Type</h3>
        <div className="flex flex-wrap gap-2">
          {TRANSITION_STYLE_NAMES.map((styleName) => {
            const isSelected = selectedTransitionType === styleName
            return (
              <button
                key={styleName}
                type="button"
                data-testid={`transition-type-${styleName}`}
                onClick={() => handleSelectStyle(styleName)}
                className={`rounded border px-3 py-2 text-sm capitalize transition-colors ${
                  isSelected
                    ? 'border-purple-500 bg-purple-900/50 text-purple-300'
                    : 'border-gray-600 bg-gray-800 text-gray-300 hover:border-gray-500'
                }`}
              >
                {styleName}
              </button>
            )
          })}
        </div>
      </div>

      {/* Parameter form */}
      {selectedTransitionType && <EffectParameterForm />}

      {/* Submit */}
      {isReady() && selectedTransitionType && (
        <div className="mt-4" data-testid="transition-submit-section">
          <button
            type="button"
            data-testid="apply-transition-btn"
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="rounded bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-500 disabled:opacity-50"
          >
            {isSubmitting ? 'Applying...' : 'Apply Transition'}
          </button>
        </div>
      )}

      {submitStatus && (
        <span
          data-testid="transition-status"
          className={`ml-3 text-sm ${submitStatus.startsWith('Error') ? 'text-red-400' : 'text-green-400'}`}
        >
          {submitStatus}
        </span>
      )}
    </div>
  )
}
