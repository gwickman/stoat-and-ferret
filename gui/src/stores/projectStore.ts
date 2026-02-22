import { create } from 'zustand'

interface ProjectState {
  selectedProjectId: string | null
  createModalOpen: boolean
  deleteModalOpen: boolean
  page: number
  pageSize: number
  setSelectedProjectId: (id: string | null) => void
  setCreateModalOpen: (open: boolean) => void
  setDeleteModalOpen: (open: boolean) => void
  setPage: (page: number) => void
  resetPage: () => void
}

export const useProjectStore = create<ProjectState>((set) => ({
  selectedProjectId: null,
  createModalOpen: false,
  deleteModalOpen: false,
  page: 0,
  pageSize: 20,
  setSelectedProjectId: (id) => set({ selectedProjectId: id }),
  setCreateModalOpen: (open) => set({ createModalOpen: open }),
  setDeleteModalOpen: (open) => set({ deleteModalOpen: open }),
  setPage: (page) => set({ page }),
  resetPage: () => set({ page: 0 }),
}))
