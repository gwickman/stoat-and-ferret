import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useComposeStore } from '../composeStore'

const mockPresets = {
  presets: [
    {
      name: 'PipTopLeft',
      description: 'Picture-in-picture top-left',
      ai_hint: 'Use for commentary overlays',
      min_inputs: 2,
      max_inputs: 2,
    },
    {
      name: 'SideBySide',
      description: 'Two inputs side by side',
      ai_hint: 'Use for comparisons',
      min_inputs: 2,
      max_inputs: 2,
    },
  ],
  total: 2,
}

beforeEach(() => {
  vi.restoreAllMocks()
  useComposeStore.getState().reset()
})

describe('composeStore', () => {
  it('fetchPresets populates presets', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify(mockPresets), { status: 200 }),
    )

    await useComposeStore.getState().fetchPresets()

    const state = useComposeStore.getState()
    expect(state.presets).toHaveLength(2)
    expect(state.presets[0].name).toBe('PipTopLeft')
    expect(state.presets[1].name).toBe('SideBySide')
    expect(state.isLoading).toBe(false)
    expect(state.error).toBeNull()
  })

  it('sets isLoading during fetch', async () => {
    let resolveFetch: (value: Response) => void
    vi.spyOn(globalThis, 'fetch').mockReturnValueOnce(
      new Promise((resolve) => {
        resolveFetch = resolve
      }),
    )

    const promise = useComposeStore.getState().fetchPresets()
    expect(useComposeStore.getState().isLoading).toBe(true)

    resolveFetch!(new Response(JSON.stringify(mockPresets), { status: 200 }))
    await promise

    expect(useComposeStore.getState().isLoading).toBe(false)
  })

  it('sets error state on API failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response('', { status: 500 }),
    )

    await useComposeStore.getState().fetchPresets()

    const state = useComposeStore.getState()
    expect(state.error).toBe('Fetch presets failed: 500')
    expect(state.isLoading).toBe(false)
  })

  it('sets error on network failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Network error'))

    await useComposeStore.getState().fetchPresets()

    const state = useComposeStore.getState()
    expect(state.error).toBe('Network error')
    expect(state.isLoading).toBe(false)
  })

  it('reset clears all state', () => {
    useComposeStore.setState({
      presets: mockPresets.presets,
      error: 'some error',
    })

    useComposeStore.getState().reset()

    const state = useComposeStore.getState()
    expect(state.presets).toHaveLength(0)
    expect(state.error).toBeNull()
    expect(state.isLoading).toBe(false)
  })
})
