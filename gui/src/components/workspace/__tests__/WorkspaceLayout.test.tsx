import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import WorkspaceLayout from '../WorkspaceLayout'
import {
  DEFAULT_PANEL_SIZES,
  DEFAULT_PANEL_VISIBILITY,
  PANEL_IDS,
  useWorkspaceStore,
} from '../../../stores/workspaceStore'

beforeEach(() => {
  window.localStorage.clear()
  useWorkspaceStore.setState({
    preset: 'edit',
    anchorPreset: 'edit',
    panelSizes: { ...DEFAULT_PANEL_SIZES },
    panelVisibility: { ...DEFAULT_PANEL_VISIBILITY },
    sizesByPreset: {},
  })
})

afterEach(() => {
  window.localStorage.clear()
})

describe('WorkspaceLayout', () => {
  it('renders all six canonical panels', () => {
    render(<WorkspaceLayout />)
    for (const panelId of PANEL_IDS) {
      expect(screen.getByTestId(`workspace-panel-${panelId}`)).toBeDefined()
    }
  })

  it('renders children inside the preview panel (Outlet integration)', () => {
    render(
      <WorkspaceLayout>
        <div data-testid="route-content">routed-page</div>
      </WorkspaceLayout>,
    )
    const previewPanel = screen.getByTestId('workspace-panel-preview')
    expect(previewPanel.querySelector('[data-testid="route-content"]')).not.toBeNull()
  })

  it('hides panels with display:none rather than removing them (LRN-140)', () => {
    render(<WorkspaceLayout />)
    // Edit preset hides render-queue and batch.
    const renderQueueContent = screen.getByTestId('workspace-panel-render-queue') as HTMLElement
    const batchContent = screen.getByTestId('workspace-panel-batch') as HTMLElement
    expect(renderQueueContent.getAttribute('data-visible')).toBe('false')
    expect(batchContent.getAttribute('data-visible')).toBe('false')
    expect(renderQueueContent.style.display).toBe('none')
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
    // Edit preset hides batch.
    const batchContent = screen.getByTestId('workspace-panel-batch') as HTMLElement
    expect(batchContent.style.pointerEvents).toBe('none')
    const previewContent = screen.getByTestId('workspace-panel-preview') as HTMLElement
    expect(previewContent.style.pointerEvents).toBe('')
  })

  it('omits the right-side separator when both render-queue and batch are hidden', () => {
    render(<WorkspaceLayout />)
    // In edit preset, both render-queue and batch are hidden — sep-main-right
    // is omitted to prevent stacked zero-width separators.
    expect(document.querySelector('[aria-label="Resize render-queue panel"]')).toBeNull()
  })

  it('omits the timeline/effects separator when only one of them is visible', () => {
    // Hide effects; timeline still visible. Separator should drop.
    useWorkspaceStore.setState((state) => ({
      panelVisibility: { ...state.panelVisibility, effects: false },
    }))
    render(<WorkspaceLayout />)
    expect(document.querySelector('[aria-label="Resize timeline panel"]')).toBeNull()
  })

  it('renders the library separator in the edit preset (library is visible)', () => {
    render(<WorkspaceLayout />)
    expect(document.querySelector('[aria-label="Resize library panel"]')).not.toBeNull()
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
