import { useEffect, useState } from 'react'

export interface VersionInfo {
  app_version: string
  core_version: string
  build_timestamp: string
  git_sha: string
  python_version: string
  database_version: string
}

export type VersionState =
  | { status: 'loading'; data: null; error: null }
  | { status: 'ready'; data: VersionInfo; error: null }
  | { status: 'error'; data: null; error: string }

export function useVersion(): VersionState {
  const [state, setState] = useState<VersionState>({
    status: 'loading',
    data: null,
    error: null,
  })

  useEffect(() => {
    let active = true

    async function load() {
      try {
        const res = await fetch('/api/v1/version')
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`)
        }
        const data = (await res.json()) as VersionInfo
        if (active) {
          setState({ status: 'ready', data, error: null })
        }
      } catch (err) {
        if (active) {
          const message = err instanceof Error ? err.message : String(err)
          setState({ status: 'error', data: null, error: message })
        }
      }
    }

    load()

    return () => {
      active = false
    }
  }, [])

  return state
}
