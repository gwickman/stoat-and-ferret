import { useWorkspace } from '../../hooks/useWorkspace'
import { PANEL_IDS } from '../../stores/workspaceStore'
import type { PanelId } from '../../stores/workspaceStore'

const PANEL_LABELS: Record<PanelId, string> = {
  library: 'Library',
  timeline: 'Timeline',
  preview: 'Preview',
  effects: 'Effects',
  'render-queue': 'Render',
  batch: 'Batch',
}

/**
 * Per-panel visibility toggle group. Each button flips the panel's visibility
 * via workspaceStore (FR-003) and persists the change to localStorage.
 */
export default function PanelVisibilityToggle() {
  const { panelVisibility, togglePanel, resetLayout } = useWorkspace()

  return (
    <div
      className="flex items-center gap-1 rounded border border-gray-700 bg-gray-900 px-2 py-1"
      data-testid="panel-visibility-toggle"
      role="group"
      aria-label="Panel visibility toggles"
    >
      {PANEL_IDS.map((panelId) => {
        const isVisible = panelVisibility[panelId] !== false
        return (
          <button
            key={panelId}
            type="button"
            onClick={() => togglePanel(panelId)}
            className={`rounded px-2 py-0.5 text-xs transition-colors ${
              isVisible
                ? 'bg-blue-600 text-white hover:bg-blue-500'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
            data-testid={`panel-toggle-${panelId}`}
            aria-pressed={isVisible}
            title={`${isVisible ? 'Hide' : 'Show'} ${PANEL_LABELS[panelId]}`}
          >
            {PANEL_LABELS[panelId]}
          </button>
        )
      })}
      <button
        type="button"
        onClick={resetLayout}
        className="ml-1 rounded border border-gray-700 px-2 py-0.5 text-xs text-gray-300 hover:bg-gray-800"
        data-testid="panel-reset-layout"
        title="Reset layout to defaults"
      >
        Reset
      </button>
    </div>
  )
}
