import { useMemo } from 'react'
import { type Effect, deriveCategory, useEffects } from '../hooks/useEffects'
import { useEffectCatalogStore } from '../stores/effectCatalogStore'

const CATEGORY_LABELS: Record<string, string> = {
  video: 'Video',
  audio: 'Audio',
  transition: 'Transition',
}

function CategoryBadge({ category }: { category: string }) {
  const colors: Record<string, string> = {
    video: 'bg-blue-600',
    audio: 'bg-green-600',
    transition: 'bg-purple-600',
  }
  return (
    <span
      className={`inline-block rounded px-2 py-0.5 text-xs font-medium text-white ${colors[category] ?? 'bg-gray-600'}`}
      data-testid="effect-category-badge"
    >
      {CATEGORY_LABELS[category] ?? category}
    </span>
  )
}

function EffectCard({
  effect,
  selected,
  viewMode,
  onSelect,
}: {
  effect: Effect
  selected: boolean
  viewMode: 'grid' | 'list'
  onSelect: (effectType: string) => void
}) {
  const category = deriveCategory(effect.effect_type)
  const hintText = Object.values(effect.ai_hints).join(' ')

  const gridClass = viewMode === 'grid' ? 'flex-col' : 'flex-row items-center gap-4'
  const selectedClass = selected
    ? 'ring-2 ring-blue-500 bg-gray-700'
    : 'bg-gray-800 hover:bg-gray-750'

  return (
    <button
      type="button"
      className={`flex w-full cursor-pointer rounded-lg border border-gray-700 p-4 text-left transition-colors ${gridClass} ${selectedClass}`}
      onClick={() => onSelect(effect.effect_type)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onSelect(effect.effect_type)
        }
      }}
      title={hintText}
      aria-describedby={`hint-${effect.effect_type}`}
      data-testid={`effect-card-${effect.effect_type}`}
    >
      <div className="flex-1">
        <div className="mb-1 flex items-center gap-2">
          <span className="font-medium text-white" data-testid="effect-name">
            {effect.name}
          </span>
          <CategoryBadge category={category} />
        </div>
        <p className="text-sm text-gray-400" data-testid="effect-description">
          {effect.description}
        </p>
      </div>
      <span id={`hint-${effect.effect_type}`} className="sr-only">
        {hintText}
      </span>
    </button>
  )
}

export default function EffectCatalog() {
  const { effects, loading, error, refetch } = useEffects()
  const {
    searchQuery,
    selectedCategory,
    selectedEffect,
    viewMode,
    setSearchQuery,
    setSelectedCategory,
    selectEffect,
    toggleViewMode,
  } = useEffectCatalogStore()

  const categories = useMemo(() => {
    const cats = new Set(effects.map((e) => deriveCategory(e.effect_type)))
    return Array.from(cats).sort()
  }, [effects])

  const filtered = useMemo(() => {
    let result = effects
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      result = result.filter((e) => e.name.toLowerCase().includes(q))
    }
    if (selectedCategory) {
      result = result.filter(
        (e) => deriveCategory(e.effect_type) === selectedCategory,
      )
    }
    return result
  }, [effects, searchQuery, selectedCategory])

  if (loading) {
    return (
      <div
        className="py-12 text-center text-gray-400"
        data-testid="effect-catalog-loading"
      >
        Loading effects...
      </div>
    )
  }

  if (error) {
    return (
      <div
        className="py-12 text-center text-red-400"
        data-testid="effect-catalog-error"
      >
        <p>{error}</p>
        <button
          type="button"
          onClick={refetch}
          className="mt-2 rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
          data-testid="effect-catalog-retry"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div data-testid="effect-catalog">
      {/* Toolbar: search, category filter, view toggle */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <input
          type="text"
          placeholder="Search effects..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
          data-testid="effect-search-input"
        />

        <select
          value={selectedCategory ?? ''}
          onChange={(e) =>
            setSelectedCategory(e.target.value || null)
          }
          className="rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
          data-testid="effect-category-filter"
        >
          <option value="">All Categories</option>
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {CATEGORY_LABELS[cat] ?? cat}
            </option>
          ))}
        </select>

        <button
          type="button"
          onClick={toggleViewMode}
          className="rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-white hover:bg-gray-700"
          data-testid="effect-view-toggle"
        >
          {viewMode === 'grid' ? 'List' : 'Grid'}
        </button>
      </div>

      {/* Effect cards */}
      {filtered.length === 0 ? (
        <div
          className="py-12 text-center text-gray-400"
          data-testid="effect-catalog-empty"
        >
          No effects match your search.
        </div>
      ) : (
        <div
          className={
            viewMode === 'grid'
              ? 'grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3'
              : 'flex flex-col gap-3'
          }
          data-testid="effect-card-list"
        >
          {filtered.map((effect) => (
            <EffectCard
              key={effect.effect_type}
              effect={effect}
              selected={selectedEffect === effect.effect_type}
              viewMode={viewMode}
              onSelect={selectEffect}
            />
          ))}
        </div>
      )}
    </div>
  )
}
