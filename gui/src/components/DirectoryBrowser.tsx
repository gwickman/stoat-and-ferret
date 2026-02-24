import { useCallback, useEffect, useState } from 'react'

interface DirectoryEntry {
  name: string
  path: string
}

interface DirectoryListResponse {
  path: string
  directories: DirectoryEntry[]
}

interface DirectoryBrowserProps {
  onSelect: (path: string) => void
  onCancel: () => void
  initialPath?: string
}

export default function DirectoryBrowser({
  onSelect,
  onCancel,
  initialPath,
}: DirectoryBrowserProps) {
  const [currentPath, setCurrentPath] = useState(initialPath ?? '')
  const [directories, setDirectories] = useState<DirectoryEntry[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchDirectories = useCallback(async (path?: string) => {
    setIsLoading(true)
    setError('')
    try {
      const params = path ? `?path=${encodeURIComponent(path)}` : ''
      const res = await fetch(`/api/v1/filesystem/directories${params}`)
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: { message: `Error: ${res.status}` } }))
        throw new Error(err.detail?.message ?? `Failed to list directories: ${res.status}`)
      }
      const data: DirectoryListResponse = await res.json()
      setCurrentPath(data.path)
      setDirectories(data.directories)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load directories')
      setDirectories([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchDirectories(initialPath || undefined)
  }, [fetchDirectories, initialPath])

  function handleNavigate(entry: DirectoryEntry) {
    fetchDirectories(entry.path)
  }

  function handleUp() {
    const parent = currentPath.replace(/[\\/][^\\/]+$/, '')
    if (parent && parent !== currentPath) {
      fetchDirectories(parent)
    }
  }

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50"
      data-testid="directory-browser-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel()
      }}
    >
      <div className="flex max-h-[80vh] w-full max-w-lg flex-col rounded-lg border border-gray-700 bg-gray-900 p-6">
        <h3 className="mb-2 text-lg font-semibold text-gray-100">
          Browse Directories
        </h3>

        <div className="mb-3 flex items-center gap-2">
          <button
            type="button"
            onClick={handleUp}
            className="shrink-0 rounded border border-gray-700 px-2 py-1 text-sm text-gray-300 hover:bg-gray-800"
            data-testid="directory-browser-up"
          >
            Up
          </button>
          <span
            className="min-w-0 truncate text-sm text-gray-400"
            data-testid="directory-browser-path"
            title={currentPath}
          >
            {currentPath}
          </span>
        </div>

        <div className="mb-4 min-h-[200px] flex-1 overflow-y-auto rounded border border-gray-700 bg-gray-800">
          {isLoading && (
            <div className="flex h-full items-center justify-center p-4 text-sm text-gray-500" data-testid="directory-browser-loading">
              Loading...
            </div>
          )}

          {!isLoading && error && (
            <div className="p-4 text-sm text-red-400" data-testid="directory-browser-error">
              {error}
            </div>
          )}

          {!isLoading && !error && directories.length === 0 && (
            <div className="flex h-full items-center justify-center p-4 text-sm text-gray-500" data-testid="directory-browser-empty">
              No subdirectories
            </div>
          )}

          {!isLoading && !error && directories.length > 0 && (
            <ul data-testid="directory-browser-list">
              {directories.map((entry) => (
                <li key={entry.path}>
                  <button
                    type="button"
                    onClick={() => handleNavigate(entry)}
                    className="w-full px-3 py-2 text-left text-sm text-gray-200 hover:bg-gray-700"
                    data-testid="directory-browser-entry"
                  >
                    📁 {entry.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded border border-gray-700 px-4 py-2 text-sm text-gray-300 hover:bg-gray-800"
            data-testid="directory-browser-cancel"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => onSelect(currentPath)}
            disabled={isLoading || !currentPath}
            className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
            data-testid="directory-browser-select"
          >
            Select This Directory
          </button>
        </div>
      </div>
    </div>
  )
}
