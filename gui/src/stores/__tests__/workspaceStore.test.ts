import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  DEFAULT_PANEL_SIZES,
  DEFAULT_PANEL_VISIBILITY,
  WORKSPACE_STORAGE_KEY,
  loadWorkspaceState,
  useWorkspaceStore,
} from '../workspaceStore'

function resetStore() {
  useWorkspaceStore.setState({
    preset: 'edit',
    panelSizes: { ...DEFAULT_PANEL_SIZES },
    panelVisibility: { ...DEFAULT_PANEL_VISIBILITY },
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
    expect(state.panelSizes).toEqual(DEFAULT_PANEL_SIZES)
    expect(state.panelVisibility).toEqual(DEFAULT_PANEL_VISIBILITY)
  })

  describe('setPreset', () => {
    it('updates preset for valid values', () => {
      useWorkspaceStore.getState().setPreset('review')
      expect(useWorkspaceStore.getState().preset).toBe('review')

      useWorkspaceStore.getState().setPreset('render')
      expect(useWorkspaceStore.getState().preset).toBe('render')

      useWorkspaceStore.getState().setPreset('custom')
      expect(useWorkspaceStore.getState().preset).toBe('custom')
    })

    it('rejects invalid preset values (INV-001)', () => {
      // @ts-expect-error -- testing runtime guard against invalid input
      useWorkspaceStore.getState().setPreset('invalid-preset')
      expect(useWorkspaceStore.getState().preset).toBe('edit')
    })

    it('persists preset change to localStorage', () => {
      useWorkspaceStore.getState().setPreset('review')
      const persisted = JSON.parse(window.localStorage.getItem(WORKSPACE_STORAGE_KEY) ?? '{}')
      expect(persisted.preset).toBe('review')
    })
  })

  describe('togglePanel', () => {
    it('flips visibility for known panels', () => {
      expect(useWorkspaceStore.getState().panelVisibility.library).toBe(true)
      useWorkspaceStore.getState().togglePanel('library')
      expect(useWorkspaceStore.getState().panelVisibility.library).toBe(false)
      useWorkspaceStore.getState().togglePanel('library')
      expect(useWorkspaceStore.getState().panelVisibility.library).toBe(true)
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
      useWorkspaceStore.getState().togglePanel('batch')
      const persisted = JSON.parse(window.localStorage.getItem(WORKSPACE_STORAGE_KEY) ?? '{}')
      expect(persisted.panelVisibility.batch).toBe(true)
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
    it('restores defaults and clears localStorage (FR-005)', () => {
      useWorkspaceStore.getState().resizePanel('library', 5)
      useWorkspaceStore.getState().setPreset('review')
      useWorkspaceStore.getState().togglePanel('batch')
      expect(window.localStorage.getItem(WORKSPACE_STORAGE_KEY)).not.toBeNull()

      useWorkspaceStore.getState().resetLayout()
      const state = useWorkspaceStore.getState()
      expect(state.preset).toBe('edit')
      expect(state.panelSizes).toEqual(DEFAULT_PANEL_SIZES)
      expect(state.panelVisibility).toEqual(DEFAULT_PANEL_VISIBILITY)
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
    })

    it('falls back to defaults on malformed JSON (FR-002 AC-3)', () => {
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
            library: false,
            'phantom-panel': true,
          },
        }),
      )
      const state = loadWorkspaceState()
      expect(state.panelSizes.library).toBe(25)
      expect(state.panelSizes.timeline).toBe(DEFAULT_PANEL_SIZES.timeline)
      expect(state.panelSizes.preview).toBe(DEFAULT_PANEL_SIZES.preview)
      expect(state.panelVisibility.library).toBe(false)
      expect((state.panelSizes as Record<string, unknown>)['phantom-panel']).toBeUndefined()
    })

    it('restores valid persisted state round-trip', () => {
      const persisted = {
        preset: 'render',
        panelSizes: { ...DEFAULT_PANEL_SIZES, preview: 60 },
        panelVisibility: { ...DEFAULT_PANEL_VISIBILITY, batch: true },
      }
      window.localStorage.setItem(WORKSPACE_STORAGE_KEY, JSON.stringify(persisted))
      const state = loadWorkspaceState()
      expect(state.preset).toBe('render')
      expect(state.panelSizes.preview).toBe(60)
      expect(state.panelVisibility.batch).toBe(true)
    })

    it('falls back to defaults when persisted preset is invalid', () => {
      window.localStorage.setItem(
        WORKSPACE_STORAGE_KEY,
        JSON.stringify({ preset: 'unknown', panelSizes: {}, panelVisibility: {} }),
      )
      expect(loadWorkspaceState().preset).toBe('edit')
    })
  })
})
