import { useCallback, useEffect, useMemo, useState } from 'react'
import { Outlet, useLocation, useSearchParams } from 'react-router-dom'
import { useRenderEvents } from '../hooks/useRenderEvents'
import {
  useKeyboardShortcuts,
  type ShortcutBinding,
} from '../hooks/useKeyboardShortcuts'
import { useWebSocket } from '../hooks/useWebSocket'
import { useSettingsStore } from '../stores/settingsStore'
import { useWorkspaceStore } from '../stores/workspaceStore'
import HealthIndicator from './HealthIndicator'
import Navigation from './Navigation'
import KeyboardShortcutOverlay from './settings/KeyboardShortcutOverlay'
import SettingsPanel from './settings/SettingsPanel'
import StatusBar from './StatusBar'
import WorkspaceLayout from './workspace/WorkspaceLayout'
import WorkspacePresetSelector from './workspace/WorkspacePresetSelector'

const VALID_URL_PRESETS = new Set(['edit', 'review', 'render'] as const)
type UrlPreset = 'edit' | 'review' | 'render'

function wsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws`
}

export default function Shell() {
  const { state: connectionState } = useWebSocket(wsUrl())
  useRenderEvents()
  const location = useLocation()
  // Per-panel routing (BL-306) makes WorkspaceLayout the primary content view,
  // but legacy URL-routed pages (`/library`, `/projects`, `/render`, etc.) are
  // still consumed by UAT journeys and direct deep links. Render the routed
  // Outlet for any non-root path so those URLs continue to work; render the
  // WorkspaceLayout for the root path (with optional `?workspace=` deep link).
  const onRootPath = location.pathname === '/' || location.pathname === ''

  // Apply ?workspace=<name> query param on mount (AC: URL preset deep link).
  // Valid values: 'edit', 'review', 'render'. Invalid values emit console.warn
  // and are ignored (localStorage preset is used instead). Missing param is a
  // no-op — workspaceStore initializes from localStorage (existing behavior).
  const [searchParams] = useSearchParams()
  const setPreset = useWorkspaceStore((s) => s.setPreset)
  useEffect(() => {
    const workspaceParam = searchParams.get('workspace')
    if (!workspaceParam) return
    if (VALID_URL_PRESETS.has(workspaceParam as UrlPreset)) {
      setPreset(workspaceParam as UrlPreset)
    } else {
      console.warn(
        `workspace: invalid preset "${workspaceParam}". Valid values are 'edit', 'review', 'render'. Using stored preset.`,
      )
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Bindings derive from settingsStore so a rebind in the settings panel
  // applies immediately (FR-004). The array identity changes when the
  // shortcut map changes, prompting `useKeyboardShortcuts` to unregister
  // the stale combos and register the new ones.
  const shortcuts = useSettingsStore((s) => s.shortcuts)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const toggleSettings = useCallback(() => setSettingsOpen((open) => !open), [])
  const closeSettings = useCallback(() => setSettingsOpen(false), [])

  const bindings = useMemo<ShortcutBinding[]>(
    () => [
      {
        combo: shortcuts['workspace.preset.edit'],
        action: 'workspace.preset.edit',
        description: 'Switch to Edit preset',
        section: 'Global',
        handler: () => useWorkspaceStore.getState().setPreset('edit'),
      },
      {
        combo: shortcuts['workspace.preset.review'],
        action: 'workspace.preset.review',
        description: 'Switch to Review preset',
        section: 'Global',
        handler: () => useWorkspaceStore.getState().setPreset('review'),
      },
      {
        combo: shortcuts['workspace.preset.render'],
        action: 'workspace.preset.render',
        description: 'Switch to Render preset',
        section: 'Global',
        handler: () => useWorkspaceStore.getState().setPreset('render'),
      },
      {
        combo: shortcuts['settings.toggle'],
        action: 'settings.toggle',
        description: 'Toggle settings panel',
        section: 'Global',
        handler: toggleSettings,
      },
    ],
    [shortcuts, toggleSettings],
  )
  useKeyboardShortcuts(bindings)

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
        {onRootPath ? <WorkspaceLayout /> : <Outlet />}
      </main>
      <StatusBar connectionState={connectionState} />
      <SettingsPanel open={settingsOpen} onClose={closeSettings} />
      <KeyboardShortcutOverlay />
    </div>
  )
}
