import { create } from 'zustand'

// ---------------------------------------------------------------------------
// Interfaces matching API contracts
// ---------------------------------------------------------------------------

/** A single render job returned by GET /api/v1/render. */
export interface RenderJob {
  id: string
  project_id: string
  status: string
  output_path: string | null
  output_format: string
  quality_preset: string
  progress: number
  eta_seconds: number | null
  speed_ratio: number | null
  frame_count: number | null
  fps: number | null
  encoder_name: string | null
  encoder_type: string | null
  /** Latest 540p frame preview URL from render.frame_available WebSocket events. */
  frame_url?: string | null
  error_message: string | null
  retry_count: number
  created_at: string
  updated_at: string
  completed_at: string | null
}

/** Queue status returned by GET /api/v1/render/queue. */
export interface QueueStatus {
  active_count: number
  pending_count: number
  max_concurrent: number
  max_queue_depth: number
  disk_available_bytes: number
  disk_total_bytes: number
  completed_today: number
  failed_today: number
}

/** A detected encoder returned by GET /api/v1/render/encoders. */
export interface Encoder {
  name: string
  codec: string
  is_hardware: boolean
  encoder_type: string
  description: string
  detected_at: string
}

/** An output format returned by GET /api/v1/render/formats. */
export interface OutputFormat {
  format: string
  extension: string
  mime_type: string
  codecs: { name: string; quality_presets: { preset: string; video_bitrate_kbps: number }[] }[]
  supports_hw_accel: boolean
  supports_two_pass: boolean
  supports_alpha: boolean
}

// ---------------------------------------------------------------------------
// Store interface
// ---------------------------------------------------------------------------

/**
 * Options for {@link RenderStoreState.setProgress}. `etaSeconds`/`speedRatio` are
 * overwritten to `null` whenever omitted; `frameCount`/`fps`/`encoderName`/`encoderType`
 * preserve their prior stored value when the key is omitted and are only overwritten
 * when the key is present (including present-with-`null`) — see BL-659 State Lifecycle
 * Specification for the two-group asymmetry this type encodes.
 */
export interface SetProgressOptions {
  jobId: string
  progress: number
  etaSeconds?: number | null
  speedRatio?: number | null
  frameCount?: number | null
  fps?: number | null
  encoderName?: string | null
  encoderType?: string | null
}

interface RenderStoreState {
  /** All render jobs. */
  jobs: RenderJob[]
  /** Queue status (null until first fetch). */
  queueStatus: QueueStatus | null
  /** Detected encoders. */
  encoders: Encoder[]
  /** Available output formats. */
  formats: OutputFormat[]
  /** Whether a fetch operation is in flight. */
  isLoading: boolean
  /** Error from the last API call. */
  error: string | null

  // Fetch actions
  fetchJobs: () => Promise<void>
  fetchQueueStatus: () => Promise<void>
  fetchEncoders: () => Promise<void>
  fetchFormats: () => Promise<void>

  // Mutation actions
  updateJob: (job: Partial<RenderJob> & { id: string }) => void
  removeJob: (jobId: string) => void
  setQueueStatus: (partial: Partial<QueueStatus>) => void
  setProgress: (options: SetProgressOptions) => void
  setFrameUrl: (jobId: string, frameUrl: string | null) => void
  reset: () => void
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

const initialState = {
  jobs: [] as RenderJob[],
  queueStatus: null as QueueStatus | null,
  encoders: [] as Encoder[],
  formats: [] as OutputFormat[],
  isLoading: false,
  error: null as string | null,
}

export const useRenderStore = create<RenderStoreState>((set) => ({
  ...initialState,

  fetchJobs: async () => {
    set({ isLoading: true, error: null })
    try {
      const res = await fetch('/api/v1/render')
      if (!res.ok) throw new Error(`Fetch jobs failed: ${res.status}`)
      const json = await res.json()
      set({ jobs: json.items, isLoading: false })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Unknown error',
        isLoading: false,
      })
    }
  },

  fetchQueueStatus: async () => {
    set({ isLoading: true, error: null })
    try {
      const res = await fetch('/api/v1/render/queue')
      if (!res.ok) throw new Error(`Fetch queue status failed: ${res.status}`)
      const json = await res.json()
      set({ queueStatus: json, isLoading: false })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Unknown error',
        isLoading: false,
      })
    }
  },

  fetchEncoders: async () => {
    set({ isLoading: true, error: null })
    try {
      const res = await fetch('/api/v1/render/encoders')
      if (!res.ok) throw new Error(`Fetch encoders failed: ${res.status}`)
      const json = await res.json()
      set({ encoders: json.encoders, isLoading: false })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Unknown error',
        isLoading: false,
      })
    }
  },

  fetchFormats: async () => {
    set({ isLoading: true, error: null })
    try {
      const res = await fetch('/api/v1/render/formats')
      if (!res.ok) throw new Error(`Fetch formats failed: ${res.status}`)
      const json = await res.json()
      set({ formats: json.formats, isLoading: false })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Unknown error',
        isLoading: false,
      })
    }
  },

  updateJob: (job) => {
    set((state) => {
      const idx = state.jobs.findIndex((j) => j.id === job.id)
      if (idx >= 0) {
        const updated = [...state.jobs]
        updated[idx] = { ...updated[idx], ...job }
        return { jobs: updated }
      }
      return { jobs: [...state.jobs, job as RenderJob] }
    })
  },

  removeJob: (jobId) => {
    set((state) => ({ jobs: state.jobs.filter((j) => j.id !== jobId) }))
  },

  setQueueStatus: (partial) => {
    set((state) => ({
      queueStatus: { ...state.queueStatus, ...partial } as QueueStatus,
    }))
  },

  setProgress: (options) => {
    const { jobId, progress, etaSeconds, speedRatio } = options
    set((state) => ({
      jobs: state.jobs.map((j) =>
        j.id === jobId
          ? {
              ...j,
              progress,
              eta_seconds: etaSeconds ?? null,
              speed_ratio: speedRatio ?? null,
              frame_count: Object.hasOwn(options, 'frameCount')
                ? (options.frameCount ?? null)
                : j.frame_count,
              fps: Object.hasOwn(options, 'fps') ? (options.fps ?? null) : j.fps,
              encoder_name: Object.hasOwn(options, 'encoderName')
                ? (options.encoderName ?? null)
                : j.encoder_name,
              encoder_type: Object.hasOwn(options, 'encoderType')
                ? (options.encoderType ?? null)
                : j.encoder_type,
            }
          : j,
      ),
    }))
  },

  setFrameUrl: (jobId, frameUrl) => {
    set((state) => ({
      jobs: state.jobs.map((j) =>
        j.id === jobId ? { ...j, frame_url: frameUrl } : j,
      ),
    }))
  },

  reset: () => set({ ...initialState }),
}))
