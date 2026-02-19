import EffectCatalog from '../components/EffectCatalog'

export default function EffectsPage() {
  return (
    <div className="p-6" data-testid="effects-page">
      <h2 className="mb-4 text-2xl font-semibold">Effects</h2>
      <EffectCatalog />
    </div>
  )
}
