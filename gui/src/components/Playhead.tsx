import { timeToPixel } from '../utils/timeline'

interface PlayheadProps {
  readonly position: number
  readonly zoom: number
  readonly scrollOffset: number
  readonly height: number
}

/** Renders a vertical playhead indicator at the current playback position. */
export default function Playhead({ position, zoom, scrollOffset, height }: Readonly<PlayheadProps>) {
  const x = timeToPixel(position, zoom, scrollOffset)

  return (
    <div
      data-testid="playhead"
      className="pointer-events-none absolute top-0 z-20 w-0.5 bg-red-500"
      style={{ left: `${x}px`, height: `${height}px` }}
      aria-hidden="true"
    />
  )
}
