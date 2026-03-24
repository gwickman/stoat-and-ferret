import { useEffect } from 'react'
import { useDebounce } from './useDebounce'
import { useEffectCatalogStore } from '../stores/effectCatalogStore'
import { useEffectFormStore } from '../stores/effectFormStore'
import type { ParameterSchema } from '../stores/effectFormStore'
import { useEffectPreviewStore } from '../stores/effectPreviewStore'

/**
 * Debounced effect preview hook.
 *
 * Watches the selected effect and form parameters, debounces changes
 * at 300ms for the filter string preview and 500ms for thumbnail generation,
 * then calls the respective APIs.
 */
/** Check whether all required schema fields are present and non-empty. */
function hasRequiredFields(
  schema: ParameterSchema | null,
  params: Record<string, unknown>,
): boolean {
  if (!schema) return false
  if (!schema.required || schema.required.length === 0) return true
  return schema.required.every((field) => {
    const val = params[field]
    return val !== undefined && val !== null && val !== ''
  })
}

export function useEffectPreview(): void {
  const selectedEffect = useEffectCatalogStore((s) => s.selectedEffect)
  const parameters = useEffectFormStore((s) => s.parameters)
  const schema = useEffectFormStore((s) => s.schema)
  const { setFilterString, setLoading, setError, setThumbnailUrl, reset } =
    useEffectPreviewStore()
  const videoPath = useEffectPreviewStore((s) => s.videoPath)

  // Debounce the parameters to avoid excessive API calls
  const debouncedParams = useDebounce(parameters, 300)
  const thumbnailDebouncedParams = useDebounce(parameters, 500)

  // Filter string preview (300ms debounce)
  useEffect(() => {
    if (!selectedEffect) {
      reset()
      return
    }

    // Skip preview when required schema fields are missing or empty
    if (!hasRequiredFields(schema, debouncedParams)) {
      reset()
      return
    }

    let active = true
    setLoading(true)

    async function fetchPreview() {
      try {
        const res = await fetch('/api/v1/effects/preview', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            effect_type: selectedEffect,
            parameters: debouncedParams,
          }),
        })
        if (!res.ok) {
          const detail = await res.json().catch(() => null)
          throw new Error(
            detail?.detail?.message ?? `Preview failed: ${res.status}`,
          )
        }
        const json: { filter_string: string } = await res.json()
        if (active) {
          setFilterString(json.filter_string)
          setLoading(false)
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : 'Unknown error')
        }
      }
    }

    fetchPreview()
    return () => {
      active = false
    }
  }, [selectedEffect, debouncedParams, schema, setFilterString, setLoading, setError, reset])

  // Thumbnail preview (500ms debounce)
  useEffect(() => {
    if (!selectedEffect || !videoPath) {
      setThumbnailUrl(null)
      return
    }

    if (!hasRequiredFields(schema, thumbnailDebouncedParams)) {
      setThumbnailUrl(null)
      return
    }

    let active = true

    async function fetchThumbnail() {
      try {
        const res = await fetch('/api/v1/effects/preview/thumbnail', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            effect_name: selectedEffect,
            video_path: videoPath,
            parameters: thumbnailDebouncedParams,
          }),
        })
        if (!res.ok) {
          if (active) setThumbnailUrl(null)
          return
        }
        const blob = await res.blob()
        if (active) {
          const url = URL.createObjectURL(blob)
          setThumbnailUrl(url)
        }
      } catch {
        if (active) setThumbnailUrl(null)
      }
    }

    fetchThumbnail()
    return () => {
      active = false
    }
  }, [selectedEffect, thumbnailDebouncedParams, videoPath, schema, setThumbnailUrl])
}
