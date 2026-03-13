/** TypeScript interfaces matching backend timeline and compose API schemas. */

/** A clip positioned on the timeline. */
export interface TimelineClip {
  id: string
  project_id: string
  source_video_id: string
  track_id: string | null
  timeline_start: number | null
  timeline_end: number | null
  in_point: number
  out_point: number
}

/** A track in the timeline. */
export interface Track {
  id: string
  project_id: string
  track_type: string
  label: string
  z_index: number
  muted: boolean
  locked: boolean
  clips: TimelineClip[]
}

/** Full timeline response from GET /api/v1/projects/{id}/timeline. */
export interface TimelineResponse {
  project_id: string
  tracks: Track[]
  duration: number
  version: number
}

/** A normalized position for a video element in a layout. */
export interface LayoutPosition {
  x: number
  y: number
  width: number
  height: number
  z_index: number
}

/** A layout preset from the compose API. */
export interface LayoutPreset {
  name: string
  description: string
  ai_hint: string
  min_inputs: number
  max_inputs: number
}

/** Response from GET /api/v1/compose/presets. */
export interface LayoutPresetListResponse {
  presets: LayoutPreset[]
  total: number
}
