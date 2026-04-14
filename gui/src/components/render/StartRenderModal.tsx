import { useCallback, useEffect, useState } from 'react'
import { useRenderStore, type OutputFormat, type Encoder } from '../../stores/renderStore'
import { useProjectStore } from '../../stores/projectStore'
import { useDebounce } from '../../hooks/useDebounce'

interface StartRenderModalProps {
  open: boolean
  onClose: () => void
  onSubmitted: () => void
}

interface FormErrors {
  output_format?: string
  quality_preset?: string
}

/** Return quality presets for the selected format by finding the first matching codec. */
function getQualityPresets(
  formats: OutputFormat[],
  selectedFormat: string,
): { preset: string; video_bitrate_kbps: number }[] {
  const fmt = formats.find((f) => f.format === selectedFormat)
  if (!fmt || fmt.codecs.length === 0) return []
  return fmt.codecs[0].quality_presets
}

/**
 * Encoders whose names are accepted by the Rust command builder (VIDEO_CODECS allowlist).
 * Used to filter both the encoder dropdown and the preview fetch, ensuring we never send
 * an unrecognised encoder name (e.g. h264_v4l2m2m) to the preview endpoint.
 */
const PREVIEW_SAFE_ENCODERS = new Set([
  'libx264', 'libx265', 'libvpx', 'libvpx-vp9', 'libaom-av1', 'prores_ks',
])

/**
 * Pick the best encoder from the given list: prefer hardware, then first in list.
 * When formats and outputFormat are provided, restricts to encoders compatible with
 * the selected format (encoder.codec in format.codecs[].name).
 * Falls back to any encoder if no compatible one is found.
 */
function selectBestEncoder(
  encoders: Encoder[],
  formats?: OutputFormat[],
  outputFormat?: string,
): string {
  if (encoders.length === 0) return ''
  let pool = encoders
  if (formats && outputFormat) {
    const fmt = formats.find((f) => f.format === outputFormat)
    if (fmt && fmt.codecs.length > 0) {
      const allowed = new Set(fmt.codecs.map((c) => c.name))
      const compatible = encoders.filter((e) => allowed.has(e.codec))
      if (compatible.length > 0) pool = compatible
    }
  }
  const hw = pool.filter((e) => e.is_hardware)
  if (hw.length > 0) return hw[0].name
  return pool[0].name
}

export default function StartRenderModal({
  open,
  onClose,
  onSubmitted,
}: StartRenderModalProps) {
  const formats = useRenderStore((s) => s.formats)
  const encoders = useRenderStore((s) => s.encoders)
  const queueStatus = useRenderStore((s) => s.queueStatus)
  const projectId = useProjectStore((s) => s.selectedProjectId)

  const [outputFormat, setOutputFormat] = useState('')
  const [qualityPreset, setQualityPreset] = useState('')
  const [encoder, setEncoder] = useState('')
  const [errors, setErrors] = useState<FormErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [previewCommand, setPreviewCommand] = useState<string | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)

  // Debounce the combination of format + quality + encoder for preview
  const debouncedFormat = useDebounce(outputFormat, 300)
  const debouncedQuality = useDebounce(qualityPreset, 300)
  const debouncedEncoder = useDebounce(encoder, 300)

  const qualityPresets = getQualityPresets(formats, outputFormat)

  // Encoder options for the dropdown: only PREVIEW_SAFE_ENCODERS that are also compatible
  // with the selected format. Restricting to safe encoders means the dropdown and the
  // preview command stay in sync — every selectable encoder produces a distinct preview.
  const formatCompatibleEncoders = (() => {
    const safe = encoders.filter((e) => PREVIEW_SAFE_ENCODERS.has(e.name))
    if (!outputFormat) return safe
    const fmt = formats.find((f) => f.format === outputFormat)
    if (!fmt || fmt.codecs.length === 0) return safe
    const allowedCodecs = new Set(fmt.codecs.map((c) => c.name))
    const compatible = safe.filter((e) => allowedCodecs.has(e.codec))
    return compatible.length > 0 ? compatible : safe
  })()

  // Auto-select defaults when formats/encoders load
  useEffect(() => {
    if (formats.length > 0 && !outputFormat) {
      setOutputFormat(formats[0].format)
    }
  }, [formats, outputFormat])

  // When format changes, reset quality to first available preset
  useEffect(() => {
    const presets = getQualityPresets(formats, outputFormat)
    if (presets.length > 0) {
      setQualityPreset(presets[0].preset)
    } else {
      setQualityPreset('')
    }
  }, [formats, outputFormat])

  // Auto-select best encoder from the safe+compatible pool whenever dependencies change
  useEffect(() => {
    const safeEncoders = encoders.filter((e) => PREVIEW_SAFE_ENCODERS.has(e.name))
    setEncoder(selectBestEncoder(safeEncoders, formats, outputFormat))
  }, [encoders, formats, outputFormat])

  // Fetch command preview when debounced values change
  useEffect(() => {
    if (!debouncedFormat || !debouncedQuality || !debouncedEncoder) {
      setPreviewCommand(null)
      return
    }

    // The encoder is always from PREVIEW_SAFE_ENCODERS (enforced by formatCompatibleEncoders
    // and selectBestEncoder). Guard defensively in case of stale debounce state.
    if (!PREVIEW_SAFE_ENCODERS.has(debouncedEncoder)) {
      setPreviewCommand(null)
      setPreviewError(null)
      return
    }
    const previewEncoder = debouncedEncoder

    let cancelled = false

    async function fetchPreview() {
      try {
        const res = await fetch('/api/v1/render/preview', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            output_format: debouncedFormat,
            quality_preset: debouncedQuality,
            encoder: previewEncoder,
          }),
        })
        if (!res.ok) {
          if (!cancelled) {
            const body = await res.json()
            setPreviewError(body?.detail?.message ?? 'Preview failed')
            setPreviewCommand(null)
          }
          return
        }
        const json = await res.json()
        if (!cancelled) {
          setPreviewCommand(json.command ?? null)
          setPreviewError(null)
        }
      } catch {
        if (!cancelled) {
          setPreviewCommand(null)
          setPreviewError(null)
        }
      }
    }

    fetchPreview()
    return () => {
      cancelled = true
    }
  }, [debouncedFormat, debouncedQuality, debouncedEncoder])

  const resetForm = useCallback(() => {
    const firstFormat = formats.length > 0 ? formats[0].format : ''
    setOutputFormat(firstFormat)
    const presets = firstFormat ? getQualityPresets(formats, firstFormat) : []
    setQualityPreset(presets.length > 0 ? presets[0].preset : '')
    const safeEncoders = encoders.filter((e) => PREVIEW_SAFE_ENCODERS.has(e.name))
    setEncoder(selectBestEncoder(safeEncoders, formats, firstFormat))
    setErrors({})
    setSubmitting(false)
    setSubmitError(null)
    setPreviewCommand(null)
    setPreviewError(null)
  }, [formats, encoders])

  const handleClose = useCallback(() => {
    resetForm()
    onClose()
  }, [resetForm, onClose])

  const handleFormatChange = (value: string) => {
    setOutputFormat(value)
    if (errors.output_format) {
      const updated = { ...errors }
      if (value) delete updated.output_format
      setErrors(updated)
    }
  }

  const handleQualityChange = (value: string) => {
    setQualityPreset(value)
    if (errors.quality_preset) {
      const updated = { ...errors }
      if (value) delete updated.quality_preset
      setErrors(updated)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const formErrors: FormErrors = {}
    if (!outputFormat) formErrors.output_format = 'Format is required'
    if (!qualityPreset) formErrors.quality_preset = 'Quality preset is required'
    setErrors(formErrors)
    if (Object.keys(formErrors).length > 0) return

    setSubmitting(true)
    setSubmitError(null)

    try {
      const res = await fetch('/api/v1/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          output_format: outputFormat,
          quality_preset: qualityPreset,
        }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        const detail = body?.detail ?? `Server error (${res.status})`
        setSubmitError(detail)
        return
      }
      resetForm()
      onSubmitted()
      onClose()
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to start render')
    } finally {
      setSubmitting(false)
    }
  }

  if (!open) return null

  // Disk space calculation
  const diskUsedPct =
    queueStatus && queueStatus.disk_total_bytes > 0
      ? ((queueStatus.disk_total_bytes - queueStatus.disk_available_bytes) /
          queueStatus.disk_total_bytes) *
        100
      : 0
  const diskWarning = diskUsedPct >= 90

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      data-testid="start-render-modal"
    >
      <div className="w-full max-w-lg rounded-lg border border-gray-700 bg-gray-800 p-6">
        <h3 className="mb-4 text-lg font-semibold text-gray-200">Start Render</h3>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Format Selector */}
          <div>
            <label htmlFor="render-format" className="mb-1 block text-sm text-gray-400">
              Output Format
            </label>
            <select
              id="render-format"
              value={outputFormat}
              onChange={(e) => handleFormatChange(e.target.value)}
              className="w-full rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-200 focus:border-blue-500 focus:outline-none"
              data-testid="select-format"
            >
              {formats.map((f) => (
                <option key={f.format} value={f.format}>
                  {f.format} (.{f.extension})
                </option>
              ))}
            </select>
            {errors.output_format && (
              <span className="mt-1 text-xs text-red-400" data-testid="error-output_format">
                {errors.output_format}
              </span>
            )}
          </div>

          {/* Quality Preset Selector */}
          <div>
            <label htmlFor="render-quality" className="mb-1 block text-sm text-gray-400">
              Quality Preset
            </label>
            <select
              id="render-quality"
              value={qualityPreset}
              onChange={(e) => handleQualityChange(e.target.value)}
              className="w-full rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-200 focus:border-blue-500 focus:outline-none"
              data-testid="select-quality"
            >
              {qualityPresets.map((p) => (
                <option key={p.preset} value={p.preset}>
                  {p.preset} ({p.video_bitrate_kbps} kbps)
                </option>
              ))}
            </select>
            {errors.quality_preset && (
              <span className="mt-1 text-xs text-red-400" data-testid="error-quality_preset">
                {errors.quality_preset}
              </span>
            )}
          </div>

          {/* Encoder Selector */}
          <div>
            <label htmlFor="render-encoder" className="mb-1 block text-sm text-gray-400">
              Encoder
            </label>
            <select
              id="render-encoder"
              value={encoder}
              onChange={(e) => setEncoder(e.target.value)}
              className="w-full rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-gray-200 focus:border-blue-500 focus:outline-none"
              data-testid="select-encoder"
            >
              {formatCompatibleEncoders.map((enc) => (
                <option key={enc.name} value={enc.name}>
                  {enc.name} {enc.is_hardware ? '(HW)' : '(SW)'}
                </option>
              ))}
            </select>
          </div>

          {/* Disk Space Bar */}
          {queueStatus && queueStatus.disk_total_bytes > 0 && (
            <div data-testid="disk-space-section">
              <label className="mb-1 block text-sm text-gray-400">Disk Space</label>
              <div className="h-3 w-full overflow-hidden rounded bg-gray-700" data-testid="disk-space-bar">
                <div
                  className={`h-full ${diskWarning ? 'bg-red-500' : 'bg-blue-500'}`}
                  style={{ width: `${Math.min(100, diskUsedPct)}%` }}
                  data-testid="disk-space-fill"
                />
              </div>
              <span className="mt-1 text-xs text-gray-400" data-testid="disk-space-text">
                {Math.round(diskUsedPct)}% used
              </span>
              {diskWarning && (
                <span className="ml-2 mt-1 text-xs text-red-400" data-testid="disk-space-warning">
                  Low disk space
                </span>
              )}
            </div>
          )}

          {/* Command Preview */}
          {previewCommand && (
            <div data-testid="command-preview-section">
              <label className="mb-1 block text-sm text-gray-400">FFmpeg Command Preview</label>
              <pre
                className="overflow-x-auto rounded border border-gray-700 bg-gray-900 p-3 text-xs text-gray-300"
                data-testid="command-preview"
              >
                <code>{previewCommand}</code>
              </pre>
            </div>
          )}
          {previewError && (
            <p className="text-sm text-red-400" data-testid="preview-error">{previewError}</p>
          )}

          {submitError && (
            <p className="text-sm text-red-400" data-testid="submit-error">
              {submitError}
            </p>
          )}

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={handleClose}
              className="rounded border border-gray-600 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700"
              data-testid="btn-cancel"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
              data-testid="btn-start-render"
            >
              {submitting ? 'Starting...' : 'Start Render'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
