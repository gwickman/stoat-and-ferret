import { render, screen } from '@testing-library/react'
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
    panelSizes: { ...DEFAULT_PANEL_SIZES },
    panelVisibility: { ...DEFAULT_PANEL_VISIBILITY },
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

    // First-run defaults: only `preview` is visible. Hidden panels (library,
    // timeline, effects, render-queue, batch) still render in the DOM but the
    // inner content is display:none so component state is preserved.
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
})
