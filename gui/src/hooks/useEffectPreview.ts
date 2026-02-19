import { useEffect } from 'react'
import { useDebounce } from './useDebounce'
import { useEffectCatalogStore } from '../stores/effectCatalogStore'
import { useEffectFormStore } from '../stores/effectFormStore'
import { useEffectPreviewStore } from '../stores/effectPreviewStore'

/**
 * Debounced effect preview hook.
 *
 * Watches the selected effect and form parameters, debounces changes
 * at 300ms, then calls the preview API to get the generated FFmpeg
 * filter string.
 */
export function useEffectPreview(): void {
  const selectedEffect = useEffectCatalogStore((s) => s.selectedEffect)
  const parameters = useEffectFormStore((s) => s.parameters)
  const { setFilterString, setLoading, setError, reset } =
    useEffectPreviewStore()

  // Debounce the parameters to avoid excessive API calls
  const debouncedParams = useDebounce(parameters, 300)

  useEffect(() => {
    if (!selectedEffect) {
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
  }, [selectedEffect, debouncedParams, setFilterString, setLoading, setError, reset])
}
