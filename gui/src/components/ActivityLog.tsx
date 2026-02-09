import { useEffect } from 'react'
import { useActivityStore } from '../stores/activityStore'

interface ActivityLogProps {
  lastMessage: MessageEvent | null
}

function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString()
  } catch {
    return iso
  }
}

function formatType(type: string): string {
  return type.replace(/_/g, ' ')
}

export default function ActivityLog({ lastMessage }: ActivityLogProps) {
  const entries = useActivityStore((s) => s.entries)
  const addEntry = useActivityStore((s) => s.addEntry)

  useEffect(() => {
    if (!lastMessage) return

    try {
      const event = JSON.parse(lastMessage.data) as {
        type: string
        payload: Record<string, unknown>
        timestamp: string
      }

      addEntry({
        type: event.type,
        timestamp: event.timestamp,
        details: event.payload,
      })
    } catch {
      // Ignore non-JSON messages
    }
  }, [lastMessage, addEntry])

  return (
    <div data-testid="activity-log">
      <h3 className="mb-3 text-lg font-semibold">Activity</h3>
      <div className="max-h-80 overflow-y-auto rounded border border-gray-700 bg-gray-900">
        {entries.length === 0 ? (
          <p className="p-4 text-sm text-gray-400" data-testid="activity-empty">
            No recent activity
          </p>
        ) : (
          <ul>
            {entries.map((entry) => (
              <li
                key={entry.id}
                className="border-b border-gray-800 px-4 py-2 last:border-b-0"
                data-testid="activity-entry"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-200">
                    {formatType(entry.type)}
                  </span>
                  <span className="text-xs text-gray-500">
                    {formatTimestamp(entry.timestamp)}
                  </span>
                </div>
                {Object.keys(entry.details).length > 0 && (
                  <p className="mt-0.5 text-xs text-gray-400">
                    {JSON.stringify(entry.details)}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
