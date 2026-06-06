import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import StartRenderModal from '../StartRenderModal'
import { useRenderStore } from '../../../stores/renderStore'
import { useProjectStore } from '../../../stores/projectStore'
import type { OutputFormat, Encoder, QueueStatus } from '../../../stores/renderStore'

const FORMATS: OutputFormat[] = [
  {
    format: 'mp4',
    extension: 'mp4',
    mime_type: 'video/mp4',
    codecs: [
      {
        name: 'h264',
        quality_presets: [
          { preset: 'draft', video_bitrate_kbps: 2000 },
          { preset: 'standard', video_bitrate_kbps: 5000 },
          { preset: 'high', video_bitrate_kbps: 10000 },
        ],
      },
    ],
    supports_hw_accel: false,
    supports_two_pass: true,
    supports_alpha: false,
  },
  {
    format: 'webm',
    extension: 'webm',
    mime_type: 'video/webm',
    codecs: [
      {
        name: 'vp9',
        quality_presets: [
          { preset: 'standard', video_bitrate_kbps: 4000 },
          { preset: 'high', video_bitrate_kbps: 8000 },
        ],
      },
    ],
    supports_hw_accel: false,
    supports_two_pass: false,
    supports_alpha: true,
  },
]

const ENCODERS: Encoder[] = [
  {
    name: 'libx264',
    codec: 'h264',
    is_hardware: false,
    encoder_type: 'software',
    description: 'H.264 software encoder',
    detected_at: '2025-06-01T00:00:00Z',
  },
  {
    name: 'h264_nvenc',
    codec: 'h264',
    is_hardware: true,
    encoder_type: 'nvidia',
    description: 'NVIDIA H.264 hardware encoder',
    detected_at: '2025-06-01T00:00:00Z',
  },
]

const QUEUE_STATUS: QueueStatus = {
  active_count: 1,
  pending_count: 2,
  max_concurrent: 4,
  max_queue_depth: 10,
  disk_available_bytes: 50_000_000_000,
  disk_total_bytes: 100_000_000_000,
  completed_today: 3,
  failed_today: 0,
}

function setupStore(overrides?: {
  formats?: OutputFormat[]
  encoders?: Encoder[]
  queueStatus?: QueueStatus | null
}) {
  const store = useRenderStore.getState()
  store.reset()
  useRenderStore.setState({
    formats: overrides?.formats ?? FORMATS,
    encoders: overrides?.encoders ?? ENCODERS,
    queueStatus: overrides?.queueStatus !== undefined ? overrides.queueStatus : QUEUE_STATUS,
  })
  useProjectStore.setState({ selectedProjectId: 'proj-1' })
}

const TIMELINE_RESPONSE = {
  project_id: 'proj-1',
  tracks: [],
  duration: 90.0,
  version: 1,
}

const defaultProps = {
  open: true,
  onClose: vi.fn(),
  onSubmitted: vi.fn(),
}

function mockFetch({
  timelineStatus = 200,
  timelineDuration = 90.0,
  previewCommand = 'ffmpeg -i input.mp4 output.mp4',
}: {
  timelineStatus?: number
  timelineDuration?: number
  previewCommand?: string
} = {}) {
  vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
    const u = typeof url === 'string' ? url : String(url)
    if (u.includes('/timeline')) {
      if (timelineStatus !== 200) {
        return Promise.resolve(
          new Response(JSON.stringify({ detail: `Timeline error ${timelineStatus}` }), {
            status: timelineStatus,
          }),
        )
      }
      return Promise.resolve(
        new Response(
          JSON.stringify({ ...TIMELINE_RESPONSE, duration: timelineDuration }),
          { status: 200 },
        ),
      )
    }
    // render/preview
    return Promise.resolve(
      new Response(JSON.stringify({ command: previewCommand }), { status: 200 }),
    )
  })
}

beforeEach(() => {
  vi.restoreAllMocks()
  setupStore()
  mockFetch()
})

describe('StartRenderModal', () => {
  // --- Format selector ---

  it('populates format selector with all formats', () => {
    render(<StartRenderModal {...defaultProps} />)
    const select = screen.getByTestId('select-format') as HTMLSelectElement
    const options = select.querySelectorAll('option')
    expect(options).toHaveLength(2)
    expect(options[0].value).toBe('mp4')
    expect(options[1].value).toBe('webm')
  })

  // --- Quality cascading ---

  it('selecting format updates quality preset options', async () => {
    render(<StartRenderModal {...defaultProps} />)

    // Initial: mp4 has 3 presets
    const qualitySelect = screen.getByTestId('select-quality') as HTMLSelectElement
    expect(qualitySelect.querySelectorAll('option')).toHaveLength(3)

    // Switch to webm: should have 2 presets
    const formatSelect = screen.getByTestId('select-format') as HTMLSelectElement
    fireEvent.change(formatSelect, { target: { value: 'webm' } })

    await waitFor(() => {
      const options = qualitySelect.querySelectorAll('option')
      expect(options).toHaveLength(2)
      expect(options[0].value).toBe('standard')
    })
  })

  // --- Encoder auto-select ---

  it('auto-selects first preview-safe encoder for the format', () => {
    render(<StartRenderModal {...defaultProps} />)
    const encoderSelect = screen.getByTestId('select-encoder') as HTMLSelectElement
    // h264_nvenc is not in PREVIEW_SAFE_ENCODERS, so only libx264 appears
    expect(encoderSelect.value).toBe('libx264')
  })

  // --- Disk space bar ---

  it('renders disk space bar from queueStatus', () => {
    render(<StartRenderModal {...defaultProps} />)
    expect(screen.getByTestId('disk-space-bar')).toBeDefined()
    const fill = screen.getByTestId('disk-space-fill')
    expect(fill.style.width).toBe('50%')
    expect(screen.getByTestId('disk-space-text').textContent).toBe('50% used')
  })

  // --- Disk space warning ---

  it('shows disk space warning when usage >= 90%', () => {
    setupStore({
      queueStatus: {
        ...QUEUE_STATUS,
        disk_available_bytes: 5_000_000_000,
        disk_total_bytes: 100_000_000_000,
      },
    })
    render(<StartRenderModal {...defaultProps} />)
    expect(screen.getByTestId('disk-space-warning')).toBeDefined()
    expect(screen.getByTestId('disk-space-warning').textContent).toBe('Low disk space')
  })

  // --- Command preview ---

  it('calls POST /render/preview for command preview', async () => {
    // Use an encoder in PREVIEW_SAFE_ENCODERS (libx264); unknown encoders skip the preview
    setupStore({ encoders: [ENCODERS[0]] })
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify({ command: 'ffmpeg -i in.mp4 out.mp4' }), { status: 200 }),
      ),
    )

    render(<StartRenderModal {...defaultProps} />)

    // Wait for debounce (300ms) + fetch to complete
    await waitFor(() => {
      const previewCalls = fetchSpy.mock.calls.filter(
        (call) => call[0] === '/api/v1/render/preview',
      )
      expect(previewCalls.length).toBeGreaterThan(0)
      expect(previewCalls[0][1]).toEqual(
        expect.objectContaining({
          method: 'POST',
        }),
      )
    })
  })

  // --- Validation ---

  it('shows inline validation error for missing required fields', async () => {
    setupStore({ formats: [] })
    render(<StartRenderModal {...defaultProps} />)
    // Wait for timeline fetch to complete so submit button is no longer disabled by loading state
    await waitFor(() => {
      expect(screen.getByTestId('btn-start-render')).not.toBeDisabled()
    })
    fireEvent.click(screen.getByTestId('btn-start-render'))
    expect(screen.getByTestId('error-output_format').textContent).toBe('Format is required')
  })

  // --- Error clearing ---

  it('clears validation errors on field change', async () => {
    setupStore({ formats: [] })
    render(<StartRenderModal {...defaultProps} />)

    // Wait for timeline fetch to complete so submit button is no longer disabled by loading state
    await waitFor(() => {
      expect(screen.getByTestId('btn-start-render')).not.toBeDisabled()
    })
    // Trigger validation
    fireEvent.click(screen.getByTestId('btn-start-render'))
    expect(screen.getByTestId('error-output_format')).toBeDefined()

    // Now set formats and re-render with formats available
    act(() => {
      useRenderStore.setState({ formats: FORMATS })
    })

    // Re-render to pick up formats
    const { unmount } = render(<StartRenderModal {...defaultProps} />)

    const formatSelect = screen.getAllByTestId('select-format')[0] as HTMLSelectElement
    fireEvent.change(formatSelect, { target: { value: 'mp4' } })

    // Error should be cleared
    expect(screen.queryByTestId('error-output_format')).toBeNull()
    unmount()
  })

  // --- Submit ---

  it('submit calls POST /render with correct payload including render_plan', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const u = typeof url === 'string' ? url : String(url)
      if (u.includes('/timeline')) {
        return Promise.resolve(
          new Response(JSON.stringify(TIMELINE_RESPONSE), { status: 200 }),
        )
      }
      if (u === '/api/v1/render') {
        return Promise.resolve(new Response(JSON.stringify({ id: 'job-1' }), { status: 201 }))
      }
      return Promise.resolve(
        new Response(JSON.stringify({ command: 'ffmpeg -i input.mp4 output.mp4' }), { status: 200 }),
      )
    })

    render(<StartRenderModal {...defaultProps} />)

    // Wait for timeline to load before clicking submit
    await waitFor(() => {
      expect(screen.getByTestId('btn-start-render')).not.toBeDisabled()
    })

    fireEvent.click(screen.getByTestId('btn-start-render'))

    await waitFor(() => {
      const submitCalls = fetchSpy.mock.calls.filter(
        (call) => call[0] === '/api/v1/render' && (call[1] as RequestInit)?.method === 'POST',
      )
      expect(submitCalls.length).toBe(1)
      const body = JSON.parse((submitCalls[0][1] as RequestInit).body as string)
      expect(body).toEqual({
        project_id: 'proj-1',
        output_format: 'mp4',
        quality_preset: 'draft',
        render_plan: JSON.stringify({ total_duration: 90.0, settings: {} }),
      })
    })
  })

  // --- Close on success ---

  it('closes modal on successful submission', async () => {
    const onClose = vi.fn()
    const onSubmitted = vi.fn()
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const u = typeof url === 'string' ? url : String(url)
      if (u.includes('/timeline')) {
        return Promise.resolve(new Response(JSON.stringify(TIMELINE_RESPONSE), { status: 200 }))
      }
      return Promise.resolve(new Response(JSON.stringify({ id: 'job-1' }), { status: 201 }))
    })

    render(<StartRenderModal open={true} onClose={onClose} onSubmitted={onSubmitted} />)

    await waitFor(() => {
      expect(screen.getByTestId('btn-start-render')).not.toBeDisabled()
    })
    fireEvent.click(screen.getByTestId('btn-start-render'))

    await waitFor(() => {
      expect(onClose).toHaveBeenCalled()
      expect(onSubmitted).toHaveBeenCalled()
    })
  })

  // --- Server error ---

  it('shows server error on 422/500 response', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const u = typeof url === 'string' ? url : String(url)
      if (u.includes('/timeline')) {
        return Promise.resolve(new Response(JSON.stringify(TIMELINE_RESPONSE), { status: 200 }))
      }
      return Promise.resolve(
        new Response(JSON.stringify({ detail: 'Invalid settings' }), { status: 422 }),
      )
    })

    render(<StartRenderModal {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByTestId('btn-start-render')).not.toBeDisabled()
    })
    fireEvent.click(screen.getByTestId('btn-start-render'))

    await waitFor(() => {
      expect(screen.getByTestId('submit-error').textContent).toBe('Invalid settings')
    })
  })

  // --- Preview error ---

  it('shows previewError when fetch returns 422 with detail.message', async () => {
    // Use an encoder in PREVIEW_SAFE_ENCODERS (libx264) so the preview fetch fires
    setupStore({ encoders: [ENCODERS[0]] })
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            detail: {
              code: 'INCOMPATIBLE_FORMAT_ENCODER',
              message: "Encoder 'libvpx' is not compatible with format 'mp4'.",
            },
          }),
          { status: 422 },
        ),
      ),
    )

    render(<StartRenderModal {...defaultProps} />)

    await waitFor(() => {
      const errorEl = screen.getByTestId('preview-error')
      expect(errorEl).toBeDefined()
      expect(errorEl.textContent).toContain("Encoder 'libvpx' is not compatible with format 'mp4'.")
    })
  })

  it('previewError is null when fetch returns 200', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify({ command: 'ffmpeg -i in.mp4 out.mp4' }), { status: 200 }),
      ),
    )

    render(<StartRenderModal {...defaultProps} />)

    await waitFor(() => {
      expect(screen.queryByTestId('preview-error')).toBeNull()
    })
  })

  // --- Modal visibility ---

  it('returns null when open is false', () => {
    const { container } = render(<StartRenderModal open={false} onClose={vi.fn()} onSubmitted={vi.fn()} />)
    expect(container.innerHTML).toBe('')
  })

  // --- Timeline fetch integration ---

  it('submit button is disabled while timelineLoading', () => {
    // Never resolve the timeline fetch so it stays in loading state
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const u = typeof url === 'string' ? url : String(url)
      if (u.includes('/timeline')) {
        return new Promise(() => {}) // never resolves
      }
      return Promise.resolve(
        new Response(JSON.stringify({ command: 'ffmpeg' }), { status: 200 }),
      )
    })

    render(<StartRenderModal {...defaultProps} />)

    expect(screen.getByTestId('btn-start-render')).toBeDisabled()
    expect(screen.getByTestId('timeline-loading')).toBeDefined()
  })

  it('submit button is disabled if timelineError is not null', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const u = typeof url === 'string' ? url : String(url)
      if (u.includes('/timeline')) {
        return Promise.resolve(
          new Response(JSON.stringify({ detail: 'Not found' }), { status: 404 }),
        )
      }
      return Promise.resolve(
        new Response(JSON.stringify({ command: 'ffmpeg' }), { status: 200 }),
      )
    })

    render(<StartRenderModal {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByTestId('timeline-error')).toBeDefined()
    })
    expect(screen.getByTestId('btn-start-render')).toBeDisabled()
  })

  it('submit button is enabled when timeline.duration is valid', async () => {
    render(<StartRenderModal {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByTestId('btn-start-render')).not.toBeDisabled()
    })
  })

  it('error message displays in modal on fetch failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const u = typeof url === 'string' ? url : String(url)
      if (u.includes('/timeline')) {
        return Promise.resolve(
          new Response(JSON.stringify({ detail: 'Timeline fetch failed' }), { status: 500 }),
        )
      }
      return Promise.resolve(
        new Response(JSON.stringify({ command: 'ffmpeg' }), { status: 200 }),
      )
    })

    render(<StartRenderModal {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByTestId('timeline-error').textContent).toBe('Timeline fetch failed')
    })
  })

  it('submit button is disabled when timeline.duration is zero', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const u = typeof url === 'string' ? url : String(url)
      if (u.includes('/timeline')) {
        return Promise.resolve(
          new Response(
            JSON.stringify({ ...TIMELINE_RESPONSE, duration: 0 }),
            { status: 200 },
          ),
        )
      }
      return Promise.resolve(
        new Response(JSON.stringify({ command: 'ffmpeg' }), { status: 200 }),
      )
    })

    render(<StartRenderModal {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByTestId('timeline-error').textContent).toBe('Timeline is empty')
    })
    expect(screen.getByTestId('btn-start-render')).toBeDisabled()
  })

  // --- Structured error detail parsing (BL-372) ---

  it('POST /api/v1/render 4xx with detail.message displays message in error UI', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const u = typeof url === 'string' ? url : String(url)
      if (u.includes('/timeline')) {
        return Promise.resolve(new Response(JSON.stringify(TIMELINE_RESPONSE), { status: 200 }))
      }
      return Promise.resolve(
        new Response(
          JSON.stringify({ detail: { code: 'INVALID_RENDER_PLAN', message: 'render_plan.total_duration required' } }),
          { status: 422 },
        ),
      )
    })

    render(<StartRenderModal {...defaultProps} />)

    await waitFor(() => expect(screen.getByTestId('btn-start-render')).not.toBeDisabled())
    fireEvent.click(screen.getByTestId('btn-start-render'))

    await waitFor(() => {
      expect(screen.getByTestId('submit-error').textContent).toBe('render_plan.total_duration required')
    })
  })

  it('POST /api/v1/render 4xx with object detail missing message falls back to String()', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const u = typeof url === 'string' ? url : String(url)
      if (u.includes('/timeline')) {
        return Promise.resolve(new Response(JSON.stringify(TIMELINE_RESPONSE), { status: 200 }))
      }
      return Promise.resolve(
        new Response(
          JSON.stringify({ detail: { code: 'SOME_ERROR' } }),
          { status: 400 },
        ),
      )
    })

    render(<StartRenderModal {...defaultProps} />)

    await waitFor(() => expect(screen.getByTestId('btn-start-render')).not.toBeDisabled())
    fireEvent.click(screen.getByTestId('btn-start-render'))

    await waitFor(() => {
      const errEl = screen.getByTestId('submit-error')
      expect(errEl.textContent).toBe('[object Object]')
    })
  })

  it('modal stays open after error; user can see error and retry', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const u = typeof url === 'string' ? url : String(url)
      if (u.includes('/timeline')) {
        return Promise.resolve(new Response(JSON.stringify(TIMELINE_RESPONSE), { status: 200 }))
      }
      return Promise.resolve(
        new Response(JSON.stringify({ detail: 'Render queue full' }), { status: 503 }),
      )
    })

    const onClose = vi.fn()
    render(<StartRenderModal open={true} onClose={onClose} onSubmitted={vi.fn()} />)

    await waitFor(() => expect(screen.getByTestId('btn-start-render')).not.toBeDisabled())
    fireEvent.click(screen.getByTestId('btn-start-render'))

    await waitFor(() => {
      expect(screen.getByTestId('submit-error').textContent).toBe('Render queue full')
    })
    // Modal must stay open: start-render-modal still present and onClose not called
    expect(screen.getByTestId('start-render-modal')).toBeDefined()
    expect(onClose).not.toHaveBeenCalled()
  })

  it('submit-error is a string and does not cause React invariant violation on structured detail', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const u = typeof url === 'string' ? url : String(url)
      if (u.includes('/timeline')) {
        return Promise.resolve(new Response(JSON.stringify(TIMELINE_RESPONSE), { status: 200 }))
      }
      return Promise.resolve(
        new Response(
          JSON.stringify({ detail: { code: 'INVALID_RENDER_PLAN', message: 'total_duration required' } }),
          { status: 422 },
        ),
      )
    })

    render(<StartRenderModal {...defaultProps} />)

    await waitFor(() => expect(screen.getByTestId('btn-start-render')).not.toBeDisabled())
    fireEvent.click(screen.getByTestId('btn-start-render'))

    await waitFor(() => {
      expect(screen.getByTestId('submit-error').textContent).toBe('total_duration required')
    })

    const objectsInvalidCalls = consoleErrorSpy.mock.calls.filter((args) =>
      String(args[0]).includes('Objects are not valid as a React child'),
    )
    expect(objectsInvalidCalls).toHaveLength(0)
    consoleErrorSpy.mockRestore()
  })

  it('POST body includes render_plan with total_duration', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      const u = typeof url === 'string' ? url : String(url)
      if (u.includes('/timeline')) {
        return Promise.resolve(new Response(JSON.stringify(TIMELINE_RESPONSE), { status: 200 }))
      }
      if (u === '/api/v1/render') {
        return Promise.resolve(new Response(JSON.stringify({ id: 'job-1' }), { status: 201 }))
      }
      return Promise.resolve(
        new Response(JSON.stringify({ command: 'ffmpeg' }), { status: 200 }),
      )
    })

    render(<StartRenderModal {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByTestId('btn-start-render')).not.toBeDisabled()
    })
    fireEvent.click(screen.getByTestId('btn-start-render'))

    await waitFor(() => {
      const renderCalls = fetchSpy.mock.calls.filter(
        (call) => call[0] === '/api/v1/render' && (call[1] as RequestInit)?.method === 'POST',
      )
      expect(renderCalls.length).toBe(1)
      const body = JSON.parse((renderCalls[0][1] as RequestInit).body as string)
      expect(body.render_plan).toBe(JSON.stringify({ total_duration: 90.0, settings: {} }))
    })
  })
})
