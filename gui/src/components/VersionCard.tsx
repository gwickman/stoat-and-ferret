import type { VersionState } from '../hooks/useVersion'

interface VersionCardProps {
  version: VersionState
}

interface RowProps {
  label: string
  value: string
}

function Row({ label, value }: RowProps) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-gray-400">{label}</span>
      <span
        className="font-mono text-gray-100"
        data-testid={`version-${label.toLowerCase().replace(/\s+/g, '-')}`}
      >
        {value}
      </span>
    </div>
  )
}

export default function VersionCard({ version }: VersionCardProps) {
  return (
    <div
      className="rounded border border-gray-700 bg-gray-900/50 p-4"
      data-testid="version-card"
    >
      <h3 className="mb-3 text-sm font-medium text-gray-200">Version</h3>
      {version.status === 'loading' && (
        <p className="text-sm text-gray-400">Loading version metadata…</p>
      )}
      {version.status === 'error' && (
        <p className="text-sm text-red-400" data-testid="version-error">
          Failed to load version: {version.error}
        </p>
      )}
      {version.status === 'ready' && (
        <div className="space-y-1.5">
          <Row label="App" value={version.data.app_version} />
          <Row label="Core" value={version.data.core_version} />
          <Row label="Python" value={version.data.python_version} />
          <Row label="Built" value={version.data.build_timestamp} />
          <Row label="App SHA" value={version.data.app_sha} />
          <Row label="Core SHA" value={version.data.git_sha} />
          <Row label="DB revision" value={version.data.database_version} />
        </div>
      )}
    </div>
  )
}
