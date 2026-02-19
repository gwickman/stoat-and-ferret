import { useEffect } from 'react'
import EffectCatalog from '../components/EffectCatalog'
import EffectParameterForm from '../components/EffectParameterForm'
import FilterPreview from '../components/FilterPreview'
import { useEffectPreview } from '../hooks/useEffectPreview'
import { useEffects } from '../hooks/useEffects'
import { useEffectCatalogStore } from '../stores/effectCatalogStore'
import type { ParameterSchema } from '../stores/effectFormStore'
import { useEffectFormStore } from '../stores/effectFormStore'

export default function EffectsPage() {
  const { effects } = useEffects()
  const selectedEffect = useEffectCatalogStore((s) => s.selectedEffect)
  const setSchema = useEffectFormStore((s) => s.setSchema)
  const resetForm = useEffectFormStore((s) => s.resetForm)

  useEffect(() => {
    if (!selectedEffect) {
      resetForm()
      return
    }
    const effect = effects.find((e) => e.effect_type === selectedEffect)
    if (effect?.parameter_schema) {
      setSchema(effect.parameter_schema as unknown as ParameterSchema)
    }
  }, [selectedEffect, effects, setSchema, resetForm])

  useEffectPreview()

  return (
    <div className="p-6" data-testid="effects-page">
      <h2 className="mb-4 text-2xl font-semibold">Effects</h2>
      <EffectCatalog />
      <EffectParameterForm />
      <FilterPreview />
    </div>
  )
}
