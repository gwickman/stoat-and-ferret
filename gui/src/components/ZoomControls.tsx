interface ZoomControlsProps {
  zoom: number
  onZoomIn: () => void
  onZoomOut: () => void
  onReset: () => void
  minZoom?: number
  maxZoom?: number
}

/** Zoom in/out controls for the timeline canvas. */
export default function ZoomControls({
  zoom,
  onZoomIn,
  onZoomOut,
  onReset,
  minZoom = 0.1,
  maxZoom = 10,
}: ZoomControlsProps) {
  return (
    <div data-testid="zoom-controls" className="flex items-center gap-1">
      <button
        type="button"
        data-testid="zoom-out"
        onClick={onZoomOut}
        disabled={zoom <= minZoom}
        className="rounded bg-gray-700 px-2 py-1 text-xs text-gray-300 hover:bg-gray-600 disabled:opacity-40"
        aria-label="Zoom out"
      >
        −
      </button>
      <button
        type="button"
        data-testid="zoom-reset"
        onClick={onReset}
        className="rounded bg-gray-700 px-2 py-1 text-xs text-gray-300 hover:bg-gray-600"
        aria-label="Reset zoom"
      >
        {Math.round(zoom * 100)}%
      </button>
      <button
        type="button"
        data-testid="zoom-in"
        onClick={onZoomIn}
        disabled={zoom >= maxZoom}
        className="rounded bg-gray-700 px-2 py-1 text-xs text-gray-300 hover:bg-gray-600 disabled:opacity-40"
        aria-label="Zoom in"
      >
        +
      </button>
    </div>
  )
}
