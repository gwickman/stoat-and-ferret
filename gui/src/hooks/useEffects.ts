import { useCallback, useEffect, useState } from 'react'

export interface Effect {
  effect_type: string
  name: string
  description: string
  parameter_schema: Record<string, unknown>
  ai_hints: Record<string, string>
  filter_preview: string
}

interface EffectListResponse {
  effects: Effect[]
  total: number
}

interface UseEffectsResult {
  effects: Effect[]
  loading: boolean
  error: string | null
  refetch: () => void
}

/**
 * Derive a display category from the effect_type string.
 *
 * Effects prefixed with "audio" or named "volume" are "audio".
 * Effects named "xfade" or "acrossfade" are "transition".
 * Everything else is "video".
 */
export function deriveCategory(effectType: string): string {
  if (
    effectType.startsWith('audio_') ||
    effectType === 'volume' ||
    effectType === 'acrossfade'
  ) {
    return 'audio'
  }
  if (effectType === 'xfade') {
    return 'transition'
  }
  return 'video'
}

export function useEffects(): UseEffectsResult {
  const [effects, setEffects] = useState<Effect[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [fetchKey, setFetchKey] = useState(0)

  const refetch = useCallback(() => setFetchKey((k) => k + 1), [])

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)

    async function fetchEffects() {
      try {
        const res = await fetch('/api/v1/effects')
        if (!res.ok) throw new Error(`Fetch failed: ${res.status}`)
        const json: EffectListResponse = await res.json()
        if (active) {
          setEffects(json.effects)
          setLoading(false)
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : 'Unknown error')
          setLoading(false)
        }
      }
    }

    fetchEffects()
    return () => {
      active = false
    }
  }, [fetchKey])

  return { effects, loading, error, refetch }
}
