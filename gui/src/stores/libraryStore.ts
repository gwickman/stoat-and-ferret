import { create } from 'zustand'

export type SortField = 'date' | 'name' | 'duration'
export type SortOrder = 'asc' | 'desc'

interface LibraryState {
  searchQuery: string
  sortField: SortField
  sortOrder: SortOrder
  page: number
  pageSize: number
  setSearchQuery: (query: string) => void
  setSortField: (field: SortField) => void
  setSortOrder: (order: SortOrder) => void
  setPage: (page: number) => void
}

export const useLibraryStore = create<LibraryState>((set) => ({
  searchQuery: '',
  sortField: 'date',
  sortOrder: 'desc',
  page: 0,
  pageSize: 20,
  setSearchQuery: (query) => set({ searchQuery: query, page: 0 }),
  setSortField: (field) => set({ sortField: field, page: 0 }),
  setSortOrder: (order) => set({ sortOrder: order, page: 0 }),
  setPage: (page) => set({ page }),
}))
