import { create } from 'zustand'

/** Workspace preset identifiers. */
export type WorkspacePreset = 'edit' | 'review' | 'render' | 'custom'

/** Named (non-custom) presets that own their canonical size definitions. */
export type NamedPreset = Exclude<WorkspacePreset, 'custom'>

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
const VALID_PRESETS: ReadonlySet<WorkspacePreset> = new Set([
  'edit',
  'review',
  'render',
  'custom',
])
const NAMED_PRESETS: ReadonlySet<NamedPreset> = new Set(['edit', 'review', 'render'])

interface PresetDefinition {
  /** Panels visible when this preset is active. All others are hidden. */
  panels: readonly PanelId[]
  /** Canonical sizes (percentages) keyed by panelId. Hidden panels get 0. */
  sizes: PanelSizes
}

const zeroSizes = (): PanelSizes => ({
  library: 0,
  timeline: 0,
  preview: 0,
  effects: 0,
  'render-queue': 0,
  batch: 0,
})

/**
 * Canonical preset definitions (BL-292). Sizes sourced from the v044 theme
 * design (Edit/Review/Render). Hidden panels carry size 0 — when toggled on
 * later the user can resize them manually (which flips preset to 'custom').
 */
export const PRESETS: Readonly<Record<NamedPreset, PresetDefinition>> = {
  edit: {
    panels: ['library', 'timeline', 'effects', 'preview'],
    sizes: { ...zeroSizes(), library: 20, timeline: 35, effects: 15, preview: 30 },
  },
  review: {
    panels: ['preview', 'timeline'],
    sizes: { ...zeroSizes(), preview: 60, timeline: 40 },
  },
  render: {
    panels: ['render-queue', 'batch', 'preview'],
    sizes: { ...zeroSizes(), 'render-queue': 30, batch: 30, preview: 40 },
  },
}

function presetVisibility(preset: NamedPreset): PanelVisibility {
  const visible = new Set<PanelId>(PRESETS[preset].panels)
  return {
    library: visible.has('library'),
    timeline: visible.has('timeline'),
    preview: visible.has('preview'),
    effects: visible.has('effects'),
    'render-queue': visible.has('render-queue'),
    batch: visible.has('batch'),
  }
}

/**
 * Default panel sizes (first-run / unconfigured state). Preview takes the full
 * width so existing routed pages render at their pre-BL-291 dimensions.
 * Switching to a named preset via `setPreset` writes the preset's canonical
 * percentages.
 */
export const DEFAULT_PANEL_SIZES: PanelSizes = {
  library: 20,
  timeline: 25,
  effects: 25,
  preview: 100,
  'render-queue': 25,
  batch: 25,
}

/**
 * Default panel visibility (first-run / unconfigured state). Only the preview
 * panel is visible so the routed Outlet renders full-width without competing
 * with empty placeholder panels. `setPreset('edit')` flips this to the Edit
 * layout when the user opts in.
 */
export const DEFAULT_PANEL_VISIBILITY: PanelVisibility = {
  library: false,
  timeline: false,
  preview: true,
  effects: false,
  'render-queue': false,
  batch: false,
}

/** Custom-mode size overrides keyed by the originating named preset. */
export type SizesByPreset = Partial<Record<NamedPreset, Partial<PanelSizes>>>

export interface WorkspaceState {
  preset: WorkspacePreset
  /**
   * Anchor named preset. When `preset === 'custom'`, this records which named
   * preset the user was on before customising — so manual resizes accumulate
   * under that preset's override map (FR-005).
   */
  anchorPreset: NamedPreset
  panelSizes: PanelSizes
  panelVisibility: PanelVisibility
  /** Per-named-preset size overrides applied on top of PRESETS[name].sizes. */
  sizesByPreset: SizesByPreset
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

const isNamedPreset = (value: unknown): value is NamedPreset =>
  typeof value === 'string' && NAMED_PRESETS.has(value as NamedPreset)

interface PersistedShape {
  preset?: unknown
  anchorPreset?: unknown
  panelSizes?: unknown
  panelVisibility?: unknown
  sizesByPreset?: unknown
}

const initialState: WorkspaceState = {
  preset: 'edit',
  anchorPreset: 'edit',
  panelSizes: { ...DEFAULT_PANEL_SIZES },
  panelVisibility: { ...DEFAULT_PANEL_VISIBILITY },
  sizesByPreset: {},
}

function cloneInitialState(): WorkspaceState {
  return {
    preset: initialState.preset,
    anchorPreset: initialState.anchorPreset,
    panelSizes: { ...initialState.panelSizes },
    panelVisibility: { ...initialState.panelVisibility },
    sizesByPreset: {},
  }
}

function sanitizeSizesByPreset(value: unknown): SizesByPreset {
  if (!value || typeof value !== 'object') return {}
  const out: SizesByPreset = {}
  for (const [presetKey, panelMap] of Object.entries(value as Record<string, unknown>)) {
    if (!isNamedPreset(presetKey)) continue
    if (!panelMap || typeof panelMap !== 'object') continue
    const overrides: Partial<PanelSizes> = {}
    for (const [panelKey, sizeValue] of Object.entries(panelMap as Record<string, unknown>)) {
      if (isPanelId(panelKey) && isFiniteSize(sizeValue)) {
        overrides[panelKey] = sizeValue
      }
    }
    if (Object.keys(overrides).length > 0) out[presetKey] = overrides
  }
  return out
}

/**
 * Hydrate workspace state from localStorage. Discards malformed JSON or
 * out-of-range values; affected fields fall back to defaults.
 */
export function loadWorkspaceState(): WorkspaceState {
  if (typeof window === 'undefined') return cloneInitialState()
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return cloneInitialState()

    const parsed = JSON.parse(raw) as PersistedShape
    if (typeof parsed !== 'object' || parsed === null) return cloneInitialState()

    const preset: WorkspacePreset =
      typeof parsed.preset === 'string' && VALID_PRESETS.has(parsed.preset as WorkspacePreset)
        ? (parsed.preset as WorkspacePreset)
        : initialState.preset

    const anchorPreset: NamedPreset = isNamedPreset(parsed.anchorPreset)
      ? parsed.anchorPreset
      : preset === 'custom'
        ? initialState.anchorPreset
        : (preset as NamedPreset)

    const panelSizes: PanelSizes = { ...DEFAULT_PANEL_SIZES }
    if (parsed.panelSizes && typeof parsed.panelSizes === 'object') {
      for (const [key, value] of Object.entries(parsed.panelSizes as Record<string, unknown>)) {
        if (isPanelId(key) && isFiniteSize(value)) panelSizes[key] = value
      }
    }

    const panelVisibility: PanelVisibility = { ...DEFAULT_PANEL_VISIBILITY }
    if (parsed.panelVisibility && typeof parsed.panelVisibility === 'object') {
      for (const [key, value] of Object.entries(parsed.panelVisibility as Record<string, unknown>)) {
        if (isPanelId(key) && typeof value === 'boolean') panelVisibility[key] = value
      }
    }

    return {
      preset,
      anchorPreset,
      panelSizes,
      panelVisibility,
      sizesByPreset: sanitizeSizesByPreset(parsed.sizesByPreset),
    }
  } catch {
    return cloneInitialState()
  }
}

function saveWorkspaceState(state: WorkspaceState): void {
  if (typeof window === 'undefined') return
  try {
    const payload: WorkspaceState = {
      preset: state.preset,
      anchorPreset: state.anchorPreset,
      panelSizes: state.panelSizes,
      panelVisibility: state.panelVisibility,
      sizesByPreset: state.sizesByPreset,
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

/** Compute the panel sizes to display for a named preset, applying any user overrides. */
function applyPresetSizes(name: NamedPreset, overrides: Partial<PanelSizes> | undefined): PanelSizes {
  const base = { ...PRESETS[name].sizes }
  if (!overrides) return base
  for (const [panelKey, value] of Object.entries(overrides)) {
    if (isPanelId(panelKey) && isFiniteSize(value)) base[panelKey] = value
  }
  return base
}

export const useWorkspaceStore = create<WorkspaceStore>((set, get) => {
  const hydrated = loadWorkspaceState()
  return {
    ...hydrated,

    setPreset: (preset) => {
      if (!VALID_PRESETS.has(preset)) {
        throw new TypeError(`setPreset: invalid preset "${String(preset)}"`)
      }
      if (preset === 'custom') {
        // No-op on sizes/visibility; only the label changes.
        if (get().preset === 'custom') return
        set({ preset })
        saveWorkspaceState(get())
        return
      }
      const overrides = get().sizesByPreset[preset]
      set({
        preset,
        anchorPreset: preset,
        panelSizes: applyPresetSizes(preset, overrides),
        panelVisibility: presetVisibility(preset),
      })
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
      const state = get()
      const anchor = state.anchorPreset
      const nextOverrides: Partial<PanelSizes> = {
        ...(state.sizesByPreset[anchor] ?? {}),
        [panelId]: size,
      }
      set({
        preset: 'custom',
        panelSizes: { ...state.panelSizes, [panelId]: size },
        sizesByPreset: { ...state.sizesByPreset, [anchor]: nextOverrides },
      })
      saveWorkspaceState(get())
    },

    resetLayout: () => {
      set(cloneInitialState())
      clearWorkspaceStorage()
    },
  }
})

/** Storage key exposed for tests and external persistence consumers. */
export const WORKSPACE_STORAGE_KEY = STORAGE_KEY
