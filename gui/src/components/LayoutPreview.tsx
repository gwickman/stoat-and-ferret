import { useComposeStore } from '../stores/composeStore'

/** Color palette for position rectangles. */
const COLORS = [
  'rgba(59, 130, 246, 0.5)', // blue
  'rgba(239, 68, 68, 0.5)', // red
  'rgba(34, 197, 94, 0.5)', // green
  'rgba(234, 179, 8, 0.5)', // yellow
]

/** Renders position rectangles representing video placement in a 16:9 preview. */
export default function LayoutPreview() {
  const positions = useComposeStore((s) => s.getActivePositions())

  return (
    <div data-testid="layout-preview">
      <h4 className="mb-2 text-sm font-medium text-gray-300">Preview</h4>
      <div
        data-testid="layout-preview-container"
        className="relative overflow-hidden rounded border border-gray-700 bg-gray-900"
        style={{ aspectRatio: '16 / 9' }}
      >
        {positions.length === 0 && (
          <p className="absolute inset-0 flex items-center justify-center text-sm text-gray-500">
            Select a preset to preview
          </p>
        )}
        {positions.map((pos, i) => (
          <div
            key={i}
            data-testid={`preview-rect-${i}`}
            className="absolute rounded border border-white/30"
            style={{
              left: `${pos.x * 100}%`,
              top: `${pos.y * 100}%`,
              width: `${pos.width * 100}%`,
              height: `${pos.height * 100}%`,
              backgroundColor: COLORS[i % COLORS.length],
              zIndex: pos.z_index,
            }}
          >
            <span className="absolute left-1 top-0.5 text-xs font-bold text-white/80">
              {i + 1}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
