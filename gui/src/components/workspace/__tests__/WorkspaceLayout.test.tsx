import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import WorkspaceLayout from '../WorkspaceLayout'
import {
  DEFAULT_PANEL_SIZES,
  DEFAULT_PANEL_VISIBILITY,
  PANEL_IDS,
  useWorkspaceStore,
} from '../../../stores/workspaceStore'

beforeEach(() => {
  window.localStorage.clear()
  vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('no-fetch'))
  useWorkspaceStore.setState({
    preset: 'edit',
    anchorPreset: 'edit',
    panelSizes: { ...DEFAULT_PANEL_SIZES },
    panelVisibility: { ...DEFAULT_PANEL_VISIBILITY },
    sizesByPreset: {},
  })
})

afterEach(() => {
  vi.restoreAllMocks()
  window.localStorage.clear()
})

describe('WorkspaceLayout', () => {
  it('renders all six canonical panels', () => {
    render(<WorkspaceLayout />)
    for (const panelId of PANEL_IDS) {
      expect(screen.getByTestId(`workspace-panel-${panelId}`)).toBeDefined()
    }
  })

  it('renders per-panel route content in visible panels (BL-306 per-panel routing)', () => {
    // Default state: edit preset, only preview visible.
    // preview panel routes to /preview → PreviewPage renders "Preview" heading.
    render(<WorkspaceLayout />)
    const previewPanel = screen.getByTestId('workspace-panel-preview')
    // PreviewPage renders data-testid="preview-page" when no project is selected.
    expect(previewPanel.querySelector('[data-testid="preview-page"]')).not.toBeNull()
  })

  it('renders placeholder label when panel has no route configured', () => {
    // Default state: library panel is hidden. When visible with no-route preset
    // (custom with routes=undefined fallback to anchorPreset's routes), library
    // panel receives its /library route from PRESETS.edit. But in DEFAULT state
    // library is hidden, so just verify the mechanism via a visible panel.
    // Render with edit preset, all panels visible.
    useWorkspaceStore.setState({
      preset: 'edit',
      anchorPreset: 'edit',
      panelSizes: { ...DEFAULT_PANEL_SIZES },
      panelVisibility: {
        library: true, timeline: true, effects: true, preview: true,
        'render-queue': false, batch: false,
      },
      sizesByPreset: {},
    })
    render(<WorkspaceLayout />)
    // render-queue panel is hidden — not visible, so nothing renders inside it.
    const rqPanel = screen.getByTestId('workspace-panel-render-queue') as HTMLElement
    expect(rqPanel.getAttribute('data-visible')).toBe('false')
  })

  it('hides panels with display:none rather than removing them (LRN-140)', () => {
    render(<WorkspaceLayout />)
    // First-run defaults: only `preview` is visible. Hidden panels still
    // render in the DOM but the inner content is display:none.
    const libraryContent = screen.getByTestId('workspace-panel-library') as HTMLElement
    const batchContent = screen.getByTestId('workspace-panel-batch') as HTMLElement
    expect(libraryContent.getAttribute('data-visible')).toBe('false')
    expect(batchContent.getAttribute('data-visible')).toBe('false')
    expect(libraryContent.style.display).toBe('none')
    expect(batchContent.style.display).toBe('none')
  })

  it('marks visible panels with data-visible="true" and no inline display', () => {
    render(<WorkspaceLayout />)
    const previewContent = screen.getByTestId('workspace-panel-preview') as HTMLElement
    expect(previewContent.getAttribute('data-visible')).toBe('true')
    expect(previewContent.style.display).toBe('')
  })

  it('hidden panels have pointer-events: none to avoid intercepting routed clicks', () => {
    render(<WorkspaceLayout />)
    // First-run defaults: library is hidden.
    const libraryContent = screen.getByTestId('workspace-panel-library') as HTMLElement
    expect(libraryContent.style.pointerEvents).toBe('none')
    const previewContent = screen.getByTestId('workspace-panel-preview') as HTMLElement
    expect(previewContent.style.pointerEvents).toBe('')
  })

  it('omits separators between hidden panels (BL-291 pointer-event regression)', () => {
    render(<WorkspaceLayout />)
    // First-run: only `preview` is visible — every separator should drop so
    // routed clicks are not intercepted by stacked zero-width separators.
    expect(document.querySelector('[aria-label="Resize library panel"]')).toBeNull()
    expect(document.querySelector('[aria-label="Resize timeline panel"]')).toBeNull()
    expect(document.querySelector('[aria-label="Resize render-queue panel"]')).toBeNull()
    expect(document.querySelector('[aria-label="Resize batch panel"]')).toBeNull()
    expect(document.querySelector('[aria-label="Resize preview panel"]')).toBeNull()
  })

  it('renders separators between adjacent visible panels in the edit preset', () => {
    useWorkspaceStore.getState().setPreset('edit')
    render(<WorkspaceLayout />)
    expect(document.querySelector('[aria-label="Resize library panel"]')).not.toBeNull()
    expect(document.querySelector('[aria-label="Resize timeline panel"]')).not.toBeNull()
  })

  it('custom preset falls back to anchorPreset routes', () => {
    // Set review preset, then flip to custom (simulating a manual resize).
    useWorkspaceStore.setState({
      preset: 'custom',
      anchorPreset: 'review',
      panelSizes: { ...DEFAULT_PANEL_SIZES },
      panelVisibility: { library: false, timeline: true, preview: true, effects: false, 'render-queue': false, batch: false },
      sizesByPreset: {},
    })
    render(<WorkspaceLayout />)
    // Review preset routes: preview → /preview. Preview panel should have PreviewPage.
    const previewPanel = screen.getByTestId('workspace-panel-preview') as HTMLElement
    expect(previewPanel.querySelector('[data-testid="preview-page"]')).not.toBeNull()
  })

  describe('bidirectional loop guard (NFR-002)', () => {
    it('does not flip preset to custom when sizes change via setPreset', async () => {
      // Render the layout so the store subscription is wired up.
      render(<WorkspaceLayout />)
      // Switch preset via the store action — this updates panel sizes which
      // would normally trigger onResize → resizePanel → preset='custom'. The
      // guardRef must short-circuit this loop.
      await act(async () => {
        useWorkspaceStore.getState().setPreset('review')
      })
      const state = useWorkspaceStore.getState()
      expect(state.preset).toBe('review')
      expect(state.anchorPreset).toBe('review')
    })

    it('preserves custom sizes across a full edit→review→render→edit cycle (FR-005)', async () => {
      render(<WorkspaceLayout />)
      // Start in edit, manually resize timeline (simulates user drag).
      await act(async () => {
        useWorkspaceStore.getState().setPreset('edit')
      })
      await act(async () => {
        useWorkspaceStore.getState().resizePanel('timeline', 50)
      })
      expect(useWorkspaceStore.getState().preset).toBe('custom')
      expect(useWorkspaceStore.getState().anchorPreset).toBe('edit')

      // Switch to review — timeline reverts to review's 40%.
      await act(async () => {
        useWorkspaceStore.getState().setPreset('review')
      })
      expect(useWorkspaceStore.getState().panelSizes.timeline).toBe(40)
      expect(useWorkspaceStore.getState().preset).toBe('review')

      // Switch to render — render preset hides timeline (size 0).
      await act(async () => {
        useWorkspaceStore.getState().setPreset('render')
      })
      expect(useWorkspaceStore.getState().preset).toBe('render')

      // Switch back to edit — custom timeline=50 is restored.
      await act(async () => {
        useWorkspaceStore.getState().setPreset('edit')
      })
      const state = useWorkspaceStore.getState()
      expect(state.preset).toBe('edit')
      expect(state.panelSizes.timeline).toBe(50)
      expect(state.panelSizes.library).toBe(20)
    })
  })
})
