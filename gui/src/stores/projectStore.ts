import { create } from 'zustand'

interface ProjectState {
  selectedProjectId: string | null
  createModalOpen: boolean
  deleteModalOpen: boolean
  setSelectedProjectId: (id: string | null) => void
  setCreateModalOpen: (open: boolean) => void
  setDeleteModalOpen: (open: boolean) => void
}

export const useProjectStore = create<ProjectState>((set) => ({
  selectedProjectId: null,
  createModalOpen: false,
  deleteModalOpen: false,
  setSelectedProjectId: (id) => set({ selectedProjectId: id }),
  setCreateModalOpen: (open) => set({ createModalOpen: open }),
  setDeleteModalOpen: (open) => set({ deleteModalOpen: open }),
}))
