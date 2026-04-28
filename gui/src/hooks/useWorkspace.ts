import { useWorkspaceStore } from '../stores/workspaceStore'
import type { PanelId, WorkspacePreset } from '../stores/workspaceStore'

/**
 * Component-level access hook for workspaceStore.
 *
 * Returns the current workspace state and action methods. Intended for use
 * inside React components — non-React modules should import the store
 * directly via `useWorkspaceStore`.
 */
export function useWorkspace() {
  const preset = useWorkspaceStore((s) => s.preset)
  const panelSizes = useWorkspaceStore((s) => s.panelSizes)
  const panelVisibility = useWorkspaceStore((s) => s.panelVisibility)
  const setPreset = useWorkspaceStore((s) => s.setPreset)
  const togglePanel = useWorkspaceStore((s) => s.togglePanel)
  const resizePanel = useWorkspaceStore((s) => s.resizePanel)
  const resetLayout = useWorkspaceStore((s) => s.resetLayout)

  return {
    preset,
    panelSizes,
    panelVisibility,
    setPreset,
    togglePanel,
    resizePanel,
    resetLayout,
  }
}

export type { PanelId, WorkspacePreset }
