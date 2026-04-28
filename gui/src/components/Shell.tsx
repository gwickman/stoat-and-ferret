import { Outlet } from 'react-router-dom'
import { useRenderEvents } from '../hooks/useRenderEvents'
import {
  useKeyboardShortcuts,
  type ShortcutBinding,
} from '../hooks/useKeyboardShortcuts'
import { useWebSocket } from '../hooks/useWebSocket'
import { useWorkspaceStore } from '../stores/workspaceStore'
import HealthIndicator from './HealthIndicator'
import Navigation from './Navigation'
import StatusBar from './StatusBar'
import WorkspaceLayout from './workspace/WorkspaceLayout'
import WorkspacePresetSelector from './workspace/WorkspacePresetSelector'

function wsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws`
}

/**
 * Module-level shortcut bindings for the Shell. Pulled from the store via
 * `getState()` so the handlers are stable references (avoids re-registering
 * on every render and preserves first-registered-wins semantics).
 */
const SHELL_SHORTCUTS: ShortcutBinding[] = [
  {
    combo: 'Ctrl+1',
    action: 'workspace.preset.edit',
    handler: () => useWorkspaceStore.getState().setPreset('edit'),
  },
  {
    combo: 'Ctrl+2',
    action: 'workspace.preset.review',
    handler: () => useWorkspaceStore.getState().setPreset('review'),
  },
  {
    combo: 'Ctrl+3',
    action: 'workspace.preset.render',
    handler: () => useWorkspaceStore.getState().setPreset('render'),
  },
]

export default function Shell() {
  const { state: connectionState } = useWebSocket(wsUrl())
  useRenderEvents()
  useKeyboardShortcuts(SHELL_SHORTCUTS)

  return (
    <div className="flex h-screen flex-col bg-gray-950 text-gray-100">
      <header className="flex items-center justify-between border-b border-gray-700 bg-gray-900 px-4 py-2">
        <Navigation />
        <div className="flex items-center gap-3">
          <WorkspacePresetSelector />
          <HealthIndicator />
        </div>
      </header>
      <main className="flex-1 overflow-hidden">
        <WorkspaceLayout>
          <Outlet />
        </WorkspaceLayout>
      </main>
      <StatusBar connectionState={connectionState} />
    </div>
  )
}
