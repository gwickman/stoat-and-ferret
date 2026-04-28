import { Group, Panel, Separator } from 'react-resizable-panels'
import type { ReactNode } from 'react'
import { useWorkspace } from '../../hooks/useWorkspace'
import type { PanelId } from '../../stores/workspaceStore'

interface WorkspacePanelProps {
  panelId: PanelId
  label: string
  minSize?: number
  children?: ReactNode
}

/**
 * Single workspace panel: respects visibility (CSS display:none, LRN-140) and
 * forwards size changes back to workspaceStore.
 */
function WorkspacePanel({ panelId, label, minSize = 10, children }: WorkspacePanelProps) {
  const { panelSizes, panelVisibility, resizePanel } = useWorkspace()
  const isVisible = panelVisibility[panelId] !== false

  return (
    <Panel
      id={panelId}
      defaultSize={panelSizes[panelId]}
      minSize={minSize}
      onResize={(size) => resizePanel(panelId, size.asPercentage)}
      className="h-full overflow-hidden"
      data-panel-id={panelId}
    >
      <div
        className="h-full w-full overflow-auto"
        data-testid={`workspace-panel-${panelId}`}
        data-visible={isVisible ? 'true' : 'false'}
        style={isVisible ? undefined : { display: 'none' }}
      >
        {children ?? (
          <div className="flex h-full items-center justify-center text-sm text-gray-500">
            {label}
          </div>
        )}
      </div>
    </Panel>
  )
}

const RESIZE_HANDLE_CLASS =
  'group flex items-center justify-center bg-gray-800 hover:bg-blue-600/70 active:bg-blue-500 transition-colors data-[separator]:h-full data-[separator]:w-1 data-[orientation=vertical]:w-full data-[orientation=vertical]:h-1'

interface WorkspaceLayoutProps {
  /** Content rendered inside the preview/main panel — typically a routed Outlet. */
  children?: ReactNode
}

/**
 * Root workspace layout. Wraps the canonical six panels (library, timeline,
 * effects, preview, render-queue, batch) in nested resizable groups and
 * persists size/visibility through workspaceStore (BL-291).
 */
export default function WorkspaceLayout({ children }: WorkspaceLayoutProps) {
  return (
    <div className="h-full w-full" data-testid="workspace-layout">
      <Group
        id="workspace-root"
        orientation="horizontal"
        className="h-full w-full bg-gray-950"
      >
        <WorkspacePanel panelId="library" label="Library" minSize={10} />

        <Separator
          id="sep-library-main"
          className={RESIZE_HANDLE_CLASS}
          aria-label="Resize library panel"
        />

        <Panel id="workspace-main" minSize={30} className="h-full overflow-hidden">
          <Group id="workspace-main-vertical" orientation="vertical" className="h-full w-full">
            <Panel id="workspace-top" minSize={20} className="overflow-hidden">
              <Group id="workspace-top-horizontal" orientation="horizontal" className="h-full w-full">
                <WorkspacePanel panelId="timeline" label="Timeline" minSize={15} />
                <Separator
                  id="sep-timeline-effects"
                  className={RESIZE_HANDLE_CLASS}
                  aria-label="Resize timeline panel"
                />
                <WorkspacePanel panelId="effects" label="Effects" minSize={15} />
              </Group>
            </Panel>

            <Separator
              id="sep-top-preview"
              className={RESIZE_HANDLE_CLASS}
              aria-label="Resize preview panel"
            />

            <WorkspacePanel panelId="preview" label="Preview" minSize={20}>
              {children}
            </WorkspacePanel>
          </Group>
        </Panel>

        <Separator
          id="sep-main-right"
          className={RESIZE_HANDLE_CLASS}
          aria-label="Resize render-queue panel"
        />

        <Panel id="workspace-right" minSize={10} className="h-full overflow-hidden">
          <Group id="workspace-right-vertical" orientation="vertical" className="h-full w-full">
            <WorkspacePanel panelId="render-queue" label="Render Queue" minSize={15} />
            <Separator
              id="sep-render-batch"
              className={RESIZE_HANDLE_CLASS}
              aria-label="Resize batch panel"
            />
            <WorkspacePanel panelId="batch" label="Batch" minSize={15} />
          </Group>
        </Panel>
      </Group>
    </div>
  )
}
