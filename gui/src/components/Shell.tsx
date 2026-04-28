import { Outlet } from 'react-router-dom'
import { useRenderEvents } from '../hooks/useRenderEvents'
import { useWebSocket } from '../hooks/useWebSocket'
import HealthIndicator from './HealthIndicator'
import Navigation from './Navigation'
import StatusBar from './StatusBar'
import WorkspaceLayout from './workspace/WorkspaceLayout'
import WorkspacePresetSelector from './workspace/WorkspacePresetSelector'
import PanelVisibilityToggle from './workspace/PanelVisibilityToggle'

function wsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws`
}

export default function Shell() {
  const { state: connectionState } = useWebSocket(wsUrl())
  useRenderEvents()

  return (
    <div className="flex h-screen flex-col bg-gray-950 text-gray-100">
      <header className="flex items-center justify-between border-b border-gray-700 bg-gray-900 px-4 py-2">
        <Navigation />
        <div className="flex items-center gap-3">
          <PanelVisibilityToggle />
          <WorkspacePresetSelector />
          <HealthIndicator />
        </div>
      </header>
      <main className="flex-1 overflow-hidden" tabIndex={0}>
        <WorkspaceLayout>
          <Outlet />
        </WorkspaceLayout>
      </main>
      <StatusBar connectionState={connectionState} />
    </div>
  )
}
