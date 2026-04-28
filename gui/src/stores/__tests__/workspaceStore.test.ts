import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  DEFAULT_PANEL_SIZES,
  DEFAULT_PANEL_VISIBILITY,
  PRESETS,
  WORKSPACE_STORAGE_KEY,
  loadWorkspaceState,
  useWorkspaceStore,
} from '../workspaceStore'

function resetStore() {
  useWorkspaceStore.setState({
    preset: 'edit',
    anchorPreset: 'edit',
    panelSizes: { ...DEFAULT_PANEL_SIZES },
    panelVisibility: { ...DEFAULT_PANEL_VISIBILITY },
    sizesByPreset: {},
  })
}

beforeEach(() => {
  window.localStorage.clear()
  resetStore()
  vi.restoreAllMocks()
})

afterEach(() => {
  window.localStorage.clear()
})

describe('workspaceStore', () => {
  it('initializes with edit preset and default sizes/visibility', () => {
    const state = useWorkspaceStore.getState()
    expect(state.preset).toBe('edit')
    expect(state.anchorPreset).toBe('edit')
    expect(state.panelSizes).toEqual(DEFAULT_PANEL_SIZES)
    expect(state.panelVisibility).toEqual(DEFAULT_PANEL_VISIBILITY)
    expect(state.sizesByPreset).toEqual({})
  })

  describe('setPreset', () => {
    it('updates preset for valid named values and applies preset sizes/visibility', () => {
      useWorkspaceStore.getState().setPreset('review')
      let state = useWorkspaceStore.getState()
      expect(state.preset).toBe('review')
      expect(state.anchorPreset).toBe('review')
      expect(state.panelSizes.preview).toBe(60)
      expect(state.panelSizes.timeline).toBe(40)
      expect(state.panelVisibility.preview).toBe(true)
      expect(state.panelVisibility.timeline).toBe(true)
      expect(state.panelVisibility.library).toBe(false)
      expect(state.panelVisibility.effects).toBe(false)
      expect(state.panelVisibility['render-queue']).toBe(false)
      expect(state.panelVisibility.batch).toBe(false)

      useWorkspaceStore.getState().setPreset('render')
      state = useWorkspaceStore.getState()
      expect(state.preset).toBe('render')
      expect(state.panelSizes['render-queue']).toBe(30)
      expect(state.panelSizes.batch).toBe(30)
      expect(state.panelSizes.preview).toBe(40)
      expect(state.panelVisibility['render-queue']).toBe(true)
      expect(state.panelVisibility.batch).toBe(true)
      expect(state.panelVisibility.preview).toBe(true)
      expect(state.panelVisibility.timeline).toBe(false)

      useWorkspaceStore.getState().setPreset('edit')
      state = useWorkspaceStore.getState()
      expect(state.preset).toBe('edit')
      expect(state.panelSizes.library).toBe(20)
      expect(state.panelSizes.timeline).toBe(35)
      expect(state.panelSizes.effects).toBe(15)
      expect(state.panelSizes.preview).toBe(30)
    })

    it('Edit preset matches PRESETS.edit (FR-001)', () => {
      useWorkspaceStore.getState().setPreset('edit')
      const state = useWorkspaceStore.getState()
      for (const panelId of PRESETS.edit.panels) {
        expect(state.panelVisibility[panelId]).toBe(true)
        expect(state.panelSizes[panelId]).toBe(PRESETS.edit.sizes[panelId])
      }
    })

    it('Review preset hides non-preset panels (FR-002)', () => {
      useWorkspaceStore.getState().setPreset('review')
      const state = useWorkspaceStore.getState()
      expect(state.panelVisibility.library).toBe(false)
      expect(state.panelVisibility.effects).toBe(false)
      expect(state.panelVisibility['render-queue']).toBe(false)
      expect(state.panelVisibility.batch).toBe(false)
    })

    it('Render preset shows render-queue, batch, preview (FR-003)', () => {
      useWorkspaceStore.getState().setPreset('render')
      const state = useWorkspaceStore.getState()
      expect(state.panelVisibility['render-queue']).toBe(true)
      expect(state.panelVisibility.batch).toBe(true)
      expect(state.panelVisibility.preview).toBe(true)
      expect(state.panelVisibility.library).toBe(false)
      expect(state.panelVisibility.timeline).toBe(false)
      expect(state.panelVisibility.effects).toBe(false)
    })

    it("setPreset('custom') only updates preset label without resizing", () => {
      useWorkspaceStore.getState().setPreset('review')
      const before = useWorkspaceStore.getState()
      useWorkspaceStore.getState().setPreset('custom')
      const after = useWorkspaceStore.getState()
      expect(after.preset).toBe('custom')
      expect(after.anchorPreset).toBe(before.anchorPreset)
      expect(after.panelSizes).toEqual(before.panelSizes)
      expect(after.panelVisibility).toEqual(before.panelVisibility)
    })

    it('throws TypeError on invalid preset values (INV-001)', () => {
      expect(() =>
        // @ts-expect-error -- testing runtime guard against invalid input
        useWorkspaceStore.getState().setPreset('invalid-preset'),
      ).toThrow(TypeError)
      expect(useWorkspaceStore.getState().preset).toBe('edit')
    })

    it('persists preset change to localStorage', () => {
      useWorkspaceStore.getState().setPreset('review')
      const persisted = JSON.parse(window.localStorage.getItem(WORKSPACE_STORAGE_KEY) ?? '{}')
      expect(persisted.preset).toBe('review')
      expect(persisted.anchorPreset).toBe('review')
    })

    it('preserves per-preset custom overrides across switches (FR-005)', () => {
      const store = useWorkspaceStore.getState()
      store.setPreset('edit')
      // Manual resize while in edit preset
      useWorkspaceStore.getState().resizePanel('timeline', 50)
      expect(useWorkspaceStore.getState().preset).toBe('custom')
      expect(useWorkspaceStore.getState().anchorPreset).toBe('edit')
      expect(useWorkspaceStore.getState().panelSizes.timeline).toBe(50)

      // Switch away to review, timeline resets to review's 40%
      useWorkspaceStore.getState().setPreset('review')
      expect(useWorkspaceStore.getState().panelSizes.timeline).toBe(40)

      // Switch back to edit, timeline restored to custom value (50)
      useWorkspaceStore.getState().setPreset('edit')
      expect(useWorkspaceStore.getState().panelSizes.timeline).toBe(50)
      expect(useWorkspaceStore.getState().panelSizes.library).toBe(20)
    })
  })

  describe('togglePanel', () => {
    it('flips visibility for known panels and preserves preset', () => {
      expect(useWorkspaceStore.getState().panelVisibility.preview).toBe(true)
      useWorkspaceStore.getState().togglePanel('preview')
      expect(useWorkspaceStore.getState().panelVisibility.preview).toBe(false)
      expect(useWorkspaceStore.getState().preset).toBe('edit')
      useWorkspaceStore.getState().togglePanel('preview')
      expect(useWorkspaceStore.getState().panelVisibility.preview).toBe(true)
    })

    it('logs warning and ignores unknown panelId', () => {
      const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
      const before = { ...useWorkspaceStore.getState().panelVisibility }
      // @ts-expect-error -- testing runtime guard against invalid input
      useWorkspaceStore.getState().togglePanel('not-a-panel')
      expect(useWorkspaceStore.getState().panelVisibility).toEqual(before)
      expect(warn).toHaveBeenCalledWith('togglePanel: unknown panelId', 'not-a-panel')
    })

    it('persists visibility changes to localStorage', () => {
      // First-run defaults: library is hidden. Toggle reveals it.
      expect(useWorkspaceStore.getState().panelVisibility.library).toBe(false)
      useWorkspaceStore.getState().togglePanel('library')
      const persisted = JSON.parse(window.localStorage.getItem(WORKSPACE_STORAGE_KEY) ?? '{}')
      expect(persisted.panelVisibility.library).toBe(true)
    })
  })

  describe('resizePanel', () => {
    it('updates size for valid values in [0, 100]', () => {
      useWorkspaceStore.getState().resizePanel('library', 35)
      expect(useWorkspaceStore.getState().panelSizes.library).toBe(35)

      useWorkspaceStore.getState().resizePanel('library', 0)
      expect(useWorkspaceStore.getState().panelSizes.library).toBe(0)

      useWorkspaceStore.getState().resizePanel('library', 100)
      expect(useWorkspaceStore.getState().panelSizes.library).toBe(100)
    })

    it('flips preset to custom on manual resize and records anchor override (FR-005)', () => {
      // Start in 'edit' preset.
      expect(useWorkspaceStore.getState().preset).toBe('edit')
      useWorkspaceStore.getState().resizePanel('library', 30)
      const state = useWorkspaceStore.getState()
      expect(state.preset).toBe('custom')
      expect(state.anchorPreset).toBe('edit')
      expect(state.sizesByPreset.edit?.library).toBe(30)
    })

    it('rejects NaN, Infinity, and out-of-range sizes (INV-002)', () => {
      const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
      const original = useWorkspaceStore.getState().panelSizes.library

      useWorkspaceStore.getState().resizePanel('library', Number.NaN)
      expect(useWorkspaceStore.getState().panelSizes.library).toBe(original)

      useWorkspaceStore.getState().resizePanel('library', Number.POSITIVE_INFINITY)
      expect(useWorkspaceStore.getState().panelSizes.library).toBe(original)

      useWorkspaceStore.getState().resizePanel('library', -5)
      expect(useWorkspaceStore.getState().panelSizes.library).toBe(original)

      useWorkspaceStore.getState().resizePanel('library', 150)
      expect(useWorkspaceStore.getState().panelSizes.library).toBe(original)

      expect(warn).toHaveBeenCalled()
    })

    it('rejects unknown panelId', () => {
      const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
      // @ts-expect-error -- testing runtime guard against invalid input
      useWorkspaceStore.getState().resizePanel('mystery', 50)
      expect(warn).toHaveBeenCalledWith('resizePanel: unknown panelId', 'mystery')
    })

    it('persists size to localStorage', () => {
      useWorkspaceStore.getState().resizePanel('preview', 42)
      const persisted = JSON.parse(window.localStorage.getItem(WORKSPACE_STORAGE_KEY) ?? '{}')
      expect(persisted.panelSizes.preview).toBe(42)
    })
  })

  describe('resetLayout', () => {
    it('restores defaults and clears localStorage', () => {
      useWorkspaceStore.getState().resizePanel('library', 5)
      useWorkspaceStore.getState().setPreset('review')
      useWorkspaceStore.getState().togglePanel('library')
      expect(window.localStorage.getItem(WORKSPACE_STORAGE_KEY)).not.toBeNull()

      useWorkspaceStore.getState().resetLayout()
      const state = useWorkspaceStore.getState()
      expect(state.preset).toBe('edit')
      expect(state.anchorPreset).toBe('edit')
      expect(state.panelSizes).toEqual(DEFAULT_PANEL_SIZES)
      expect(state.panelVisibility).toEqual(DEFAULT_PANEL_VISIBILITY)
      expect(state.sizesByPreset).toEqual({})
      expect(window.localStorage.getItem(WORKSPACE_STORAGE_KEY)).toBeNull()
    })
  })

  describe('loadWorkspaceState', () => {
    it('returns defaults when localStorage is empty (first-run)', () => {
      window.localStorage.clear()
      const state = loadWorkspaceState()
      expect(state.preset).toBe('edit')
      expect(state.panelSizes).toEqual(DEFAULT_PANEL_SIZES)
      expect(state.panelVisibility).toEqual(DEFAULT_PANEL_VISIBILITY)
      expect(state.sizesByPreset).toEqual({})
    })

    it('falls back to defaults on malformed JSON', () => {
      window.localStorage.setItem(WORKSPACE_STORAGE_KEY, 'this-is-not-json{')
      const state = loadWorkspaceState()
      expect(state.preset).toBe('edit')
      expect(state.panelSizes).toEqual(DEFAULT_PANEL_SIZES)
      expect(state.panelVisibility).toEqual(DEFAULT_PANEL_VISIBILITY)
    })

    it('discards invalid panel IDs and out-of-range sizes', () => {
      window.localStorage.setItem(
        WORKSPACE_STORAGE_KEY,
        JSON.stringify({
          preset: 'edit',
          panelSizes: {
            library: 25,
            timeline: 'not-a-number',
            preview: 200,
            'phantom-panel': 50,
          },
          panelVisibility: {
            library: true,
            'phantom-panel': true,
          },
        }),
      )
      const state = loadWorkspaceState()
      expect(state.panelSizes.library).toBe(25)
      expect(state.panelSizes.timeline).toBe(DEFAULT_PANEL_SIZES.timeline)
      expect(state.panelSizes.preview).toBe(DEFAULT_PANEL_SIZES.preview)
      expect(state.panelVisibility.library).toBe(true)
      expect((state.panelSizes as Record<string, unknown>)['phantom-panel']).toBeUndefined()
    })

    it('restores valid persisted state round-trip including sizesByPreset', () => {
      const persisted = {
        preset: 'render',
        anchorPreset: 'render',
        panelSizes: { ...DEFAULT_PANEL_SIZES, preview: 60 },
        panelVisibility: { ...DEFAULT_PANEL_VISIBILITY, library: true },
        sizesByPreset: { edit: { timeline: 50 } },
      }
      window.localStorage.setItem(WORKSPACE_STORAGE_KEY, JSON.stringify(persisted))
      const state = loadWorkspaceState()
      expect(state.preset).toBe('render')
      expect(state.anchorPreset).toBe('render')
      expect(state.panelSizes.preview).toBe(60)
      expect(state.panelVisibility.library).toBe(true)
      expect(state.sizesByPreset.edit?.timeline).toBe(50)
    })

    it('falls back to defaults when persisted preset is invalid', () => {
      window.localStorage.setItem(
        WORKSPACE_STORAGE_KEY,
        JSON.stringify({ preset: 'unknown', panelSizes: {}, panelVisibility: {} }),
      )
      expect(loadWorkspaceState().preset).toBe('edit')
    })

    it('discards malformed sizesByPreset entries', () => {
      window.localStorage.setItem(
        WORKSPACE_STORAGE_KEY,
        JSON.stringify({
          preset: 'edit',
          sizesByPreset: {
            edit: { timeline: 50, 'phantom-panel': 10, library: 'oops' },
            unknown: { preview: 25 },
          },
        }),
      )
      const state = loadWorkspaceState()
      expect(state.sizesByPreset.edit?.timeline).toBe(50)
      expect(state.sizesByPreset.edit?.library).toBeUndefined()
      expect((state.sizesByPreset as Record<string, unknown>).unknown).toBeUndefined()
    })
  })
})
