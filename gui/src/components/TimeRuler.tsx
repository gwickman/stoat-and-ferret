import { useMemo } from 'react'
import { timeToPixel, getMarkerInterval, formatRulerTime, BASE_PIXELS_PER_SECOND } from '../utils/timeline'

interface TimeRulerProps {
  duration: number
  zoom: number
  scrollOffset: number
  canvasWidth: number
  pixelsPerSecond?: number
}

/** Horizontal time ruler with zoom-responsive markers above the tracks. */
export default function TimeRuler({
  duration,
  zoom,
  scrollOffset,
  canvasWidth,
  pixelsPerSecond = BASE_PIXELS_PER_SECOND,
}: TimeRulerProps) {
  const interval = useMemo(() => getMarkerInterval(zoom, pixelsPerSecond), [zoom, pixelsPerSecond])

  const markers = useMemo(() => {
    const result: { time: number; x: number }[] = []
    // Start from the first marker visible (or just before) the viewport
    const startTime = Math.max(0, Math.floor(scrollOffset / (pixelsPerSecond * zoom) / interval) * interval)
    for (let t = startTime; t <= duration; t += interval) {
      const x = timeToPixel(t, zoom, scrollOffset, pixelsPerSecond)
      if (x > canvasWidth + 10) break
      if (x >= -10) {
        result.push({ time: parseFloat(t.toFixed(4)), x })
      }
    }
    return result
  }, [duration, zoom, scrollOffset, canvasWidth, pixelsPerSecond, interval])

  return (
    <div
      data-testid="time-ruler"
      className="relative h-6 border-b border-gray-600 bg-gray-800"
    >
      {markers.map((marker) => (
        <div
          key={marker.time}
          data-testid={`ruler-marker-${marker.time}`}
          className="absolute top-0 flex h-full flex-col items-center"
          style={{ left: `${marker.x}px` }}
        >
          <div className="h-2 w-px bg-gray-500" />
          <span className="text-[10px] text-gray-400">{formatRulerTime(marker.time)}</span>
        </div>
      ))}
    </div>
  )
}
