import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useEffects, deriveCategory } from '../useEffects'

beforeEach(() => {
  vi.restoreAllMocks()
})

const mockEffects = [
  {
    effect_type: 'text_overlay',
    name: 'Text Overlay',
    description: 'Add text overlays',
    parameter_schema: {},
    ai_hints: { text: 'hint' },
    filter_preview: 'drawtext=text=Sample',
  },
  {
    effect_type: 'volume',
    name: 'Volume',
    description: 'Adjust audio volume',
    parameter_schema: {},
    ai_hints: { volume: 'hint' },
    filter_preview: 'volume=1.5',
  },
]

describe('useEffects', () => {
  it('fetches effects successfully', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ effects: mockEffects, total: 2 }), {
        status: 200,
      }),
    )

    const { result } = renderHook(() => useEffects())

    expect(result.current.loading).toBe(true)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.effects).toHaveLength(2)
    expect(result.current.effects[0].name).toBe('Text Overlay')
    expect(result.current.error).toBeNull()
  })

  it('handles fetch errors', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useEffects())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Network error')
    expect(result.current.effects).toHaveLength(0)
  })

  it('handles non-ok response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('', { status: 500 }),
    )

    const { result } = renderHook(() => useEffects())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Fetch failed: 500')
  })
})

describe('deriveCategory', () => {
  it('classifies audio effects', () => {
    expect(deriveCategory('audio_fade')).toBe('audio')
    expect(deriveCategory('audio_mix')).toBe('audio')
    expect(deriveCategory('audio_ducking')).toBe('audio')
    expect(deriveCategory('volume')).toBe('audio')
    expect(deriveCategory('acrossfade')).toBe('audio')
  })

  it('classifies transition effects', () => {
    expect(deriveCategory('xfade')).toBe('transition')
  })

  it('classifies video effects', () => {
    expect(deriveCategory('text_overlay')).toBe('video')
    expect(deriveCategory('speed_control')).toBe('video')
    expect(deriveCategory('video_fade')).toBe('video')
  })
})
