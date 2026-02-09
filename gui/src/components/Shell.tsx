import { Outlet } from 'react-router-dom'
import { useWebSocket } from '../hooks/useWebSocket'
import HealthIndicator from './HealthIndicator'
import Navigation from './Navigation'
import StatusBar from './StatusBar'

function wsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws`
}

export default function Shell() {
  const { state: connectionState } = useWebSocket(wsUrl())

  return (
    <div className="flex h-screen flex-col bg-gray-950 text-gray-100">
      <header className="flex items-center justify-between border-b border-gray-700 bg-gray-900 px-4 py-2">
        <Navigation />
        <HealthIndicator />
      </header>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
      <StatusBar connectionState={connectionState} />
    </div>
  )
}
