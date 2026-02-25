import { useCallback, useEffect, useState } from 'react'
import ClipSelector from '../components/ClipSelector'
import EffectCatalog from '../components/EffectCatalog'
import EffectParameterForm from '../components/EffectParameterForm'
import EffectStack from '../components/EffectStack'
import FilterPreview from '../components/FilterPreview'
import TransitionPanel from '../components/TransitionPanel'
import { useEffectPreview } from '../hooks/useEffectPreview'
import { useEffects } from '../hooks/useEffects'
import type { Clip } from '../hooks/useProjects'
import { useProjects } from '../hooks/useProjects'
import { useEffectCatalogStore } from '../stores/effectCatalogStore'
import type { ParameterSchema } from '../stores/effectFormStore'
import { useEffectFormStore } from '../stores/effectFormStore'
import type { AppliedEffect } from '../stores/effectStackStore'
import { useEffectStackStore } from '../stores/effectStackStore'

type WorkshopTab = 'effects' | 'transitions'

export default function EffectsPage() {
  const { effects } = useEffects()
  const { projects } = useProjects()
  const selectedEffect = useEffectCatalogStore((s) => s.selectedEffect)
  const selectEffect = useEffectCatalogStore((s) => s.selectEffect)
  const setSchema = useEffectFormStore((s) => s.setSchema)
  const resetForm = useEffectFormStore((s) => s.resetForm)
  const formParameters = useEffectFormStore((s) => s.parameters)

  const selectedClipId = useEffectStackStore((s) => s.selectedClipId)
  const stackEffects = useEffectStackStore((s) => s.effects)
  const stackLoading = useEffectStackStore((s) => s.isLoading)
  const stackSelectClip = useEffectStackStore((s) => s.selectClip)
  const fetchStackEffects = useEffectStackStore((s) => s.fetchEffects)
  const removeStackEffect = useEffectStackStore((s) => s.removeEffect)

  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
  const [clips, setClips] = useState<Clip[]>([])
  const [applyStatus, setApplyStatus] = useState<string | null>(null)
  const [editIndex, setEditIndex] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<WorkshopTab>('effects')

  // Auto-select first project
  useEffect(() => {
    if (projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id)
    }
  }, [projects, selectedProjectId])

  // Fetch clips when project changes
  useEffect(() => {
    if (!selectedProjectId) return
    let active = true

    async function loadClips() {
      try {
        const res = await fetch(`/api/v1/projects/${selectedProjectId}/clips`)
        if (!res.ok) return
        const json = await res.json()
        if (active) setClips(json.clips ?? [])
      } catch {
        // Silently handle fetch errors
      }
    }

    loadClips()
    return () => { active = false }
  }, [selectedProjectId])

  // Fetch effect stack when clip is selected
  useEffect(() => {
    if (selectedProjectId && selectedClipId) {
      fetchStackEffects(selectedProjectId, selectedClipId)
    }
  }, [selectedProjectId, selectedClipId, fetchStackEffects])

  // Set form schema when effect selected
  useEffect(() => {
    if (!selectedEffect) {
      resetForm()
      setEditIndex(null)
      return
    }
    const effect = effects.find((e) => e.effect_type === selectedEffect)
    if (effect?.parameter_schema) {
      setSchema(effect.parameter_schema as unknown as ParameterSchema)
    }
  }, [selectedEffect, effects, setSchema, resetForm])

  useEffectPreview()

  const handleClipSelect = useCallback(
    (clipId: string) => {
      stackSelectClip(clipId)
      setEditIndex(null)
    },
    [stackSelectClip],
  )

  const handleApply = useCallback(async () => {
    if (!selectedProjectId || !selectedClipId || !selectedEffect) return
    setApplyStatus(null)

    const url = editIndex !== null
      ? `/api/v1/projects/${selectedProjectId}/clips/${selectedClipId}/effects/${editIndex}`
      : `/api/v1/projects/${selectedProjectId}/clips/${selectedClipId}/effects`

    const method = editIndex !== null ? 'PATCH' : 'POST'
    const body = editIndex !== null
      ? { parameters: formParameters }
      : { effect_type: selectedEffect, parameters: formParameters }

    try {
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const detail = await res.json().catch(() => null)
        setApplyStatus(`Error: ${detail?.detail?.message || res.statusText}`)
        return
      }

      setApplyStatus(editIndex !== null ? 'Effect updated!' : 'Effect applied!')
      setEditIndex(null)
      selectEffect(null)
      resetForm()
      await fetchStackEffects(selectedProjectId, selectedClipId)
      setTimeout(() => setApplyStatus(null), 2000)
    } catch (err) {
      setApplyStatus(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }, [
    selectedProjectId,
    selectedClipId,
    selectedEffect,
    formParameters,
    editIndex,
    selectEffect,
    resetForm,
    fetchStackEffects,
  ])

  const handleEdit = useCallback(
    (index: number, effect: AppliedEffect) => {
      setEditIndex(index)
      selectEffect(effect.effect_type)
      // Pre-fill form with existing parameters after schema is set
      const defn = effects.find((e) => e.effect_type === effect.effect_type)
      if (defn?.parameter_schema) {
        setSchema(defn.parameter_schema as unknown as ParameterSchema)
        // Override defaults with existing values
        for (const [key, value] of Object.entries(effect.parameters)) {
          useEffectFormStore.getState().setParameter(key, value)
        }
      }
    },
    [effects, selectEffect, setSchema],
  )

  const handleRemove = useCallback(
    (index: number) => {
      if (selectedProjectId && selectedClipId) {
        removeStackEffect(selectedProjectId, selectedClipId, index)
      }
    },
    [selectedProjectId, selectedClipId, removeStackEffect],
  )

  return (
    <div className="p-6" data-testid="effects-page">
      <h2 className="mb-4 text-2xl font-semibold">Effects</h2>

      {/* Project selector */}
      {projects.length > 1 && (
        <div className="mb-4">
          <label htmlFor="project-select" className="mr-2 text-sm text-gray-400">
            Project:
          </label>
          <select
            id="project-select"
            data-testid="project-select"
            value={selectedProjectId ?? ''}
            onChange={(e) => {
              setSelectedProjectId(e.target.value)
              stackSelectClip(null)
              setClips([])
            }}
            className="rounded border border-gray-600 bg-gray-800 px-2 py-1 text-sm text-white"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Tab toggle */}
      <div className="mb-4 flex gap-1 rounded-lg border border-gray-700 bg-gray-900 p-1" data-testid="workshop-tabs">
        <button
          type="button"
          data-testid="tab-effects"
          onClick={() => setActiveTab('effects')}
          className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'effects'
              ? 'bg-gray-700 text-white'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          Effects
        </button>
        <button
          type="button"
          data-testid="tab-transitions"
          onClick={() => setActiveTab('transitions')}
          className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'transitions'
              ? 'bg-gray-700 text-white'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          Transitions
        </button>
      </div>

      {/* Effects tab content */}
      {activeTab === 'effects' && (
        <>
          {/* Clip selector */}
          <ClipSelector
            clips={clips}
            selectedClipId={selectedClipId}
            onSelect={handleClipSelect}
          />

          {/* Effect catalog + form + preview */}
          <EffectCatalog />
          <EffectParameterForm />
          <FilterPreview />

          {/* Apply button */}
          {selectedClipId && selectedEffect && (
            <div className="mt-4" data-testid="apply-section">
              <button
                type="button"
                data-testid="apply-effect-btn"
                onClick={handleApply}
                className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
              >
                {editIndex !== null ? 'Update Effect' : 'Apply to Clip'}
              </button>
              {editIndex !== null && (
                <button
                  type="button"
                  data-testid="cancel-edit-btn"
                  onClick={() => {
                    setEditIndex(null)
                    selectEffect(null)
                    resetForm()
                  }}
                  className="ml-2 rounded bg-gray-700 px-4 py-2 text-sm text-gray-300 hover:bg-gray-600"
                >
                  Cancel Edit
                </button>
              )}
              {applyStatus && (
                <span
                  data-testid="apply-status"
                  className={`ml-3 text-sm ${applyStatus.startsWith('Error') ? 'text-red-400' : 'text-green-400'}`}
                >
                  {applyStatus}
                </span>
              )}
            </div>
          )}

          {/* Visual preview placeholder */}
          {selectedClipId && (
            <p className="mt-2 text-xs text-gray-500" data-testid="visual-preview-placeholder">
              Visual preview coming in a future version
            </p>
          )}

          {/* Effect stack for selected clip */}
          {selectedClipId && (
            <EffectStack
              effects={stackEffects}
              isLoading={stackLoading}
              onEdit={handleEdit}
              onRemove={handleRemove}
            />
          )}
        </>
      )}

      {/* Transitions tab content */}
      {activeTab === 'transitions' && selectedProjectId && (
        <TransitionPanel projectId={selectedProjectId} clips={clips} />
      )}
    </div>
  )
}
