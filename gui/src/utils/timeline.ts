/** Shared coordinate math utilities for the timeline canvas. */

/** Default pixels per second at zoom level 1.0. */
export const BASE_PIXELS_PER_SECOND = 100

/**
 * Convert a time value to a pixel position on the canvas.
 *
 * @param time - Time in seconds
 * @param zoom - Zoom multiplier (1.0 = default)
 * @param scrollOffset - Horizontal scroll offset in pixels
 * @param pixelsPerSecond - Base pixels per second (before zoom)
 * @returns Pixel x-coordinate on the canvas
 */
export function timeToPixel(
  time: number,
  zoom: number,
  scrollOffset: number,
  pixelsPerSecond: number = BASE_PIXELS_PER_SECOND,
): number {
  return time * pixelsPerSecond * zoom - scrollOffset
}

/**
 * Convert a pixel position back to a time value.
 *
 * @param pixel - Pixel x-coordinate on the canvas
 * @param zoom - Zoom multiplier (1.0 = default)
 * @param scrollOffset - Horizontal scroll offset in pixels
 * @param pixelsPerSecond - Base pixels per second (before zoom)
 * @returns Time in seconds
 */
export function pixelToTime(
  pixel: number,
  zoom: number,
  scrollOffset: number,
  pixelsPerSecond: number = BASE_PIXELS_PER_SECOND,
): number {
  if (zoom === 0 || pixelsPerSecond === 0) return 0
  return (pixel + scrollOffset) / (pixelsPerSecond * zoom)
}

/**
 * Calculate appropriate time marker interval based on zoom level.
 *
 * Returns the interval in seconds between ruler markers.
 * At high zoom, markers are closer (e.g. 0.1s); at low zoom, farther (e.g. 10s, 60s).
 */
export function getMarkerInterval(zoom: number, pixelsPerSecond: number = BASE_PIXELS_PER_SECOND): number {
  const effectivePps = pixelsPerSecond * zoom
  // Target ~80-150px between markers
  const intervals = [0.1, 0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300]
  for (const interval of intervals) {
    const gap = interval * effectivePps
    if (gap >= 80) return interval
  }
  return 600
}

/**
 * Format a time value for display on the ruler.
 *
 * @param seconds - Time in seconds
 * @returns Formatted string like "0:00", "1:30", "0:00.5"
 */
export function formatRulerTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (secs === Math.floor(secs)) {
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }
  return `${mins}:${secs.toFixed(1).padStart(4, '0')}`
}
