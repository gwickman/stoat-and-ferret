import { create } from 'zustand'

const MAX_ENTRIES = 50

export interface ActivityEntry {
  id: string
  type: string
  timestamp: string
  details: Record<string, unknown>
}

interface ActivityState {
  entries: ActivityEntry[]
  addEntry: (entry: Omit<ActivityEntry, 'id'>) => void
}

let nextId = 0

export const useActivityStore = create<ActivityState>((set) => ({
  entries: [],
  addEntry: (entry) =>
    set((state) => {
      const newEntry = { ...entry, id: String(nextId++) }
      const updated = [newEntry, ...state.entries]
      return { entries: updated.slice(0, MAX_ENTRIES) }
    }),
}))
