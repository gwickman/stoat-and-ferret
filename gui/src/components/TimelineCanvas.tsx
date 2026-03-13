import { useState, useRef, useCallback } from 'react'
import type { Track as TrackType } from '../types/timeline'
import TimeRuler from './TimeRuler'
import Track from './Track'
import ZoomControls from './ZoomControls'

interface TimelineCanvasProps {
  tracks: TrackType[]
  duration: number
}

const MIN_ZOOM = 0.1
const MAX_ZOOM = 10
const ZOOM_STEP = 0.25

/** Main timeline canvas container with ruler, tracks, zoom, and horizontal scroll. */
export default function TimelineCanvas({ tracks, duration }: TimelineCanvasProps) {
  const [zoom, setZoom] = useState(1)
  const [scrollOffset, setScrollOffset] = useState(0)
  const scrollRef = useRef<HTMLDivElement>(null)

  const handleScroll = useCallback(() => {
    if (scrollRef.current) {
      setScrollOffset(scrollRef.current.scrollLeft)
    }
  }, [])

  const handleZoomIn = useCallback(() => {
    setZoom((z) => Math.min(MAX_ZOOM, z + ZOOM_STEP))
  }, [])

  const handleZoomOut = useCallback(() => {
    setZoom((z) => Math.max(MIN_ZOOM, z - ZOOM_STEP))
  }, [])

  const handleZoomReset = useCallback(() => {
    setZoom(1)
  }, [])

  const sortedTracks = [...tracks].sort((a, b) => a.z_index - b.z_index)

  if (tracks.length === 0) {
    return (
      <div data-testid="timeline-canvas-empty" className="rounded border border-gray-700 p-8 text-center">
        <p className="text-gray-400">No tracks on the timeline. Add clips to get started.</p>
      </div>
    )
  }

  return (
    <div data-testid="timeline-canvas" className="rounded border border-gray-700">
      <div className="flex items-center justify-between border-b border-gray-700 bg-gray-800 px-2 py-1">
        <span className="text-xs text-gray-400" data-testid="canvas-duration">
          Duration: {duration.toFixed(1)}s
        </span>
        <ZoomControls
          zoom={zoom}
          onZoomIn={handleZoomIn}
          onZoomOut={handleZoomOut}
          onReset={handleZoomReset}
          minZoom={MIN_ZOOM}
          maxZoom={MAX_ZOOM}
        />
      </div>
      <div
        ref={scrollRef}
        data-testid="canvas-scroll-area"
        className="overflow-x-auto"
        onScroll={handleScroll}
      >
        <div style={{ minWidth: `${duration * 100 * zoom}px` }}>
          <TimeRuler
            duration={duration}
            zoom={zoom}
            scrollOffset={scrollOffset}
            canvasWidth={scrollRef.current?.clientWidth ?? 800}
          />
          <div className="flex flex-col" data-testid="canvas-tracks">
            {sortedTracks.map((track) => (
              <Track
                key={track.id}
                track={track}
                zoom={zoom}
                scrollOffset={scrollOffset}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
