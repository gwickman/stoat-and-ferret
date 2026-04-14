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

const defaultProps = {
  open: true,
  onClose: vi.fn(),
  onSubmitted: vi.fn(),
}

beforeEach(() => {
  vi.restoreAllMocks()
  setupStore()
  vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
    Promise.resolve(
      new Response(JSON.stringify({ command: 'ffmpeg -i input.mp4 output.mp4' }), { status: 200 }),
    ),
  )
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

  it('shows inline validation error for missing required fields', () => {
    setupStore({ formats: [] })
    render(<StartRenderModal {...defaultProps} />)
    fireEvent.click(screen.getByTestId('btn-start-render'))
    expect(screen.getByTestId('error-output_format').textContent).toBe('Format is required')
  })

  // --- Error clearing ---

  it('clears validation errors on field change', async () => {
    setupStore({ formats: [] })
    render(<StartRenderModal {...defaultProps} />)

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

  it('submit calls POST /render with correct payload', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify({ id: 'job-1' }), { status: 201 })),
    )

    render(<StartRenderModal {...defaultProps} />)
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
      })
    })
  })

  // --- Close on success ---

  it('closes modal on successful submission', async () => {
    const onClose = vi.fn()
    const onSubmitted = vi.fn()
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify({ id: 'job-1' }), { status: 201 })),
    )

    render(<StartRenderModal open={true} onClose={onClose} onSubmitted={onSubmitted} />)
    fireEvent.click(screen.getByTestId('btn-start-render'))

    await waitFor(() => {
      expect(onClose).toHaveBeenCalled()
      expect(onSubmitted).toHaveBeenCalled()
    })
  })

  // --- Server error ---

  it('shows server error on 422/500 response', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify({ detail: 'Invalid settings' }), { status: 422 }),
      ),
    )

    render(<StartRenderModal {...defaultProps} />)
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
})
