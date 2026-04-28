import { create } from 'zustand'

/** Workspace preset identifiers (BL-292 will populate the size mappings). */
export type WorkspacePreset = 'edit' | 'review' | 'render' | 'custom'

/** Canonical workspace panel identifiers. */
export const PANEL_IDS = [
  'library',
  'timeline',
  'preview',
  'effects',
  'render-queue',
  'batch',
] as const

export type PanelId = (typeof PANEL_IDS)[number]

export type PanelSizes = Record<PanelId, number>
export type PanelVisibility = Record<PanelId, boolean>

const STORAGE_KEY = 'stoat-workspace-layout'
const VALID_PRESETS: ReadonlySet<WorkspacePreset> = new Set(['edit', 'review', 'render', 'custom'])

/** Default panel sizes (percentages, summing to 100 within each PanelGroup). */
export const DEFAULT_PANEL_SIZES: PanelSizes = {
  library: 20,
  timeline: 25,
  effects: 25,
  preview: 30,
  'render-queue': 50,
  batch: 50,
}

/** Default panel visibility — Edit preset shows core panels, hides render/batch. */
export const DEFAULT_PANEL_VISIBILITY: PanelVisibility = {
  library: true,
  timeline: true,
  preview: true,
  effects: true,
  'render-queue': false,
  batch: false,
}

export interface WorkspaceState {
  preset: WorkspacePreset
  panelSizes: PanelSizes
  panelVisibility: PanelVisibility
}

export interface WorkspaceStore extends WorkspaceState {
  setPreset: (preset: WorkspacePreset) => void
  togglePanel: (panelId: PanelId) => void
  resizePanel: (panelId: PanelId, size: number) => void
  resetLayout: () => void
}

const isPanelId = (value: unknown): value is PanelId =>
  typeof value === 'string' && (PANEL_IDS as readonly string[]).includes(value)

const isFiniteSize = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 100

interface PersistedShape {
  preset?: unknown
  panelSizes?: unknown
  panelVisibility?: unknown
}

const initialState: WorkspaceState = {
  preset: 'edit',
  panelSizes: { ...DEFAULT_PANEL_SIZES },
  panelVisibility: { ...DEFAULT_PANEL_VISIBILITY },
}

/**
 * Hydrate workspace state from localStorage. Discards malformed JSON or
 * out-of-range values; affected fields fall back to defaults (FR-002, INV-002).
 */
export function loadWorkspaceState(): WorkspaceState {
  if (typeof window === 'undefined') return { ...initialState, panelSizes: { ...initialState.panelSizes }, panelVisibility: { ...initialState.panelVisibility } }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...initialState, panelSizes: { ...initialState.panelSizes }, panelVisibility: { ...initialState.panelVisibility } }

    const parsed = JSON.parse(raw) as PersistedShape
    if (typeof parsed !== 'object' || parsed === null) {
      return { ...initialState, panelSizes: { ...initialState.panelSizes }, panelVisibility: { ...initialState.panelVisibility } }
    }

    const preset: WorkspacePreset =
      typeof parsed.preset === 'string' && VALID_PRESETS.has(parsed.preset as WorkspacePreset)
        ? (parsed.preset as WorkspacePreset)
        : initialState.preset

    const panelSizes: PanelSizes = { ...DEFAULT_PANEL_SIZES }
    if (parsed.panelSizes && typeof parsed.panelSizes === 'object') {
      for (const [key, value] of Object.entries(parsed.panelSizes as Record<string, unknown>)) {
        if (isPanelId(key) && isFiniteSize(value)) {
          panelSizes[key] = value
        }
      }
    }

    const panelVisibility: PanelVisibility = { ...DEFAULT_PANEL_VISIBILITY }
    if (parsed.panelVisibility && typeof parsed.panelVisibility === 'object') {
      for (const [key, value] of Object.entries(parsed.panelVisibility as Record<string, unknown>)) {
        if (isPanelId(key) && typeof value === 'boolean') {
          panelVisibility[key] = value
        }
      }
    }

    return { preset, panelSizes, panelVisibility }
  } catch {
    return { ...initialState, panelSizes: { ...initialState.panelSizes }, panelVisibility: { ...initialState.panelVisibility } }
  }
}

function saveWorkspaceState(state: WorkspaceState): void {
  if (typeof window === 'undefined') return
  try {
    const payload: WorkspaceState = {
      preset: state.preset,
      panelSizes: state.panelSizes,
      panelVisibility: state.panelVisibility,
    }
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  } catch {
    // localStorage unavailable (private mode, quota exceeded) — silently degrade.
  }
}

function clearWorkspaceStorage(): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.removeItem(STORAGE_KEY)
  } catch {
    // localStorage unavailable — silently degrade.
  }
}

export const useWorkspaceStore = create<WorkspaceStore>((set, get) => {
  const hydrated = loadWorkspaceState()
  return {
    ...hydrated,

    setPreset: (preset) => {
      if (!VALID_PRESETS.has(preset)) return
      set({ preset })
      saveWorkspaceState(get())
    },

    togglePanel: (panelId) => {
      if (!isPanelId(panelId)) {
        console.warn('togglePanel: unknown panelId', panelId)
        return
      }
      set((state) => ({
        panelVisibility: {
          ...state.panelVisibility,
          [panelId]: !state.panelVisibility[panelId],
        },
      }))
      saveWorkspaceState(get())
    },

    resizePanel: (panelId, size) => {
      if (!isPanelId(panelId)) {
        console.warn('resizePanel: unknown panelId', panelId)
        return
      }
      if (!isFiniteSize(size)) {
        console.warn('resizePanel: rejected non-finite or out-of-range size', { panelId, size })
        return
      }
      set((state) => ({
        panelSizes: { ...state.panelSizes, [panelId]: size },
      }))
      saveWorkspaceState(get())
    },

    resetLayout: () => {
      set({
        preset: 'edit',
        panelSizes: { ...DEFAULT_PANEL_SIZES },
        panelVisibility: { ...DEFAULT_PANEL_VISIBILITY },
      })
      clearWorkspaceStorage()
    },
  }
})

/** Storage key exposed for tests and external persistence consumers. */
export const WORKSPACE_STORAGE_KEY = STORAGE_KEY
