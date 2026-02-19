import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'

interface TabDef {
  label: string
  path: string
  checkUrl: string
}

const TABS: TabDef[] = [
  { label: 'Dashboard', path: '/', checkUrl: '/health/live' },
  { label: 'Library', path: '/library', checkUrl: '/api/v1/videos' },
  { label: 'Projects', path: '/projects', checkUrl: '/api/v1/projects' },
  { label: 'Effects', path: '/effects', checkUrl: '/api/v1/effects' },
]

export default function Navigation() {
  const [availableTabs, setAvailableTabs] = useState<TabDef[]>([])

  useEffect(() => {
    let active = true

    async function checkTabs() {
      const results = await Promise.all(
        TABS.map(async (tab) => {
          try {
            const res = await fetch(tab.checkUrl, { method: 'HEAD' })
            return { tab, available: res.ok || res.status === 405 }
          } catch {
            return { tab, available: false }
          }
        }),
      )
      if (active) {
        setAvailableTabs(results.filter((r) => r.available).map((r) => r.tab))
      }
    }

    checkTabs()
    return () => {
      active = false
    }
  }, [])

  return (
    <nav className="flex gap-1" data-testid="navigation">
      {availableTabs.map((tab) => (
        <NavLink
          key={tab.path}
          to={tab.path}
          end={tab.path === '/'}
          className={({ isActive }) =>
            `px-4 py-2 rounded-t text-sm font-medium transition-colors ${
              isActive
                ? 'bg-gray-800 text-white'
                : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
            }`
          }
          data-testid={`nav-tab-${tab.label.toLowerCase()}`}
        >
          {tab.label}
        </NavLink>
      ))}
    </nav>
  )
}
