import { create } from 'zustand'

export type ViewMode = 'grid' | 'list'

interface EffectCatalogState {
  searchQuery: string
  selectedCategory: string | null
  selectedEffect: string | null
  viewMode: ViewMode
  setSearchQuery: (query: string) => void
  setSelectedCategory: (category: string | null) => void
  selectEffect: (effectType: string | null) => void
  toggleViewMode: () => void
}

export const useEffectCatalogStore = create<EffectCatalogState>((set) => ({
  searchQuery: '',
  selectedCategory: null,
  selectedEffect: null,
  viewMode: 'grid',
  setSearchQuery: (query) => set({ searchQuery: query }),
  setSelectedCategory: (category) => set({ selectedCategory: category }),
  selectEffect: (effectType) => set({ selectedEffect: effectType }),
  toggleViewMode: () =>
    set((state) => ({
      viewMode: state.viewMode === 'grid' ? 'list' : 'grid',
    })),
}))
