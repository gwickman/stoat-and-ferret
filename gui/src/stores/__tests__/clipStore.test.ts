import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useClipStore } from '../clipStore'

const mockClips = [
  {
    id: 'clip-1',
    project_id: 'proj-1',
    source_video_id: 'vid-1',
    in_point: 0,
    out_point: 90,
    timeline_position: 0,
    created_at: '2025-01-15T10:00:00Z',
    updated_at: '2025-01-15T10:00:00Z',
  },
]

beforeEach(() => {
  vi.restoreAllMocks()
  useClipStore.getState().reset()
})

describe('clipStore', () => {
  it('fetchClips populates clips state', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ clips: mockClips, total: 1 }), { status: 200 }),
    )

    await useClipStore.getState().fetchClips('proj-1')

    const state = useClipStore.getState()
    expect(state.clips).toHaveLength(1)
    expect(state.clips[0].id).toBe('clip-1')
    expect(state.isLoading).toBe(false)
    expect(state.error).toBeNull()
  })

  it('createClip calls POST endpoint and refreshes clips', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
    // POST response
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify(mockClips[0]), { status: 201 }),
    )
    // GET response for refresh
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ clips: mockClips, total: 1 }), { status: 200 }),
    )

    await useClipStore.getState().createClip('proj-1', {
      source_video_id: 'vid-1',
      in_point: 0,
      out_point: 90,
      timeline_position: 0,
    })

    expect(fetchSpy).toHaveBeenCalledTimes(2)
    const [postUrl, postOpts] = fetchSpy.mock.calls[0]
    expect(postUrl).toBe('/api/v1/projects/proj-1/clips')
    expect(postOpts?.method).toBe('POST')

    const state = useClipStore.getState()
    expect(state.clips).toHaveLength(1)
    expect(state.isLoading).toBe(false)
  })

  it('updateClip calls PATCH endpoint and refreshes clips', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
    // PATCH response
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ ...mockClips[0], out_point: 120 }), { status: 200 }),
    )
    // GET response for refresh
    fetchSpy.mockResolvedValueOnce(
      new Response(
        JSON.stringify({ clips: [{ ...mockClips[0], out_point: 120 }], total: 1 }),
        { status: 200 },
      ),
    )

    await useClipStore.getState().updateClip('proj-1', 'clip-1', { out_point: 120 })

    expect(fetchSpy).toHaveBeenCalledTimes(2)
    const [patchUrl, patchOpts] = fetchSpy.mock.calls[0]
    expect(patchUrl).toBe('/api/v1/projects/proj-1/clips/clip-1')
    expect(patchOpts?.method).toBe('PATCH')

    const state = useClipStore.getState()
    expect(state.clips[0].out_point).toBe(120)
    expect(state.isLoading).toBe(false)
  })

  it('deleteClip calls DELETE endpoint and refreshes clips', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
    // DELETE response
    fetchSpy.mockResolvedValueOnce(new Response('', { status: 200 }))
    // GET response for refresh
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ clips: [], total: 0 }), { status: 200 }),
    )

    await useClipStore.getState().deleteClip('proj-1', 'clip-1')

    expect(fetchSpy).toHaveBeenCalledTimes(2)
    const [deleteUrl, deleteOpts] = fetchSpy.mock.calls[0]
    expect(deleteUrl).toBe('/api/v1/projects/proj-1/clips/clip-1')
    expect(deleteOpts?.method).toBe('DELETE')

    const state = useClipStore.getState()
    expect(state.clips).toHaveLength(0)
    expect(state.isLoading).toBe(false)
  })

  it('sets error state on API failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response('', { status: 500 }),
    )

    await useClipStore.getState().fetchClips('proj-1')

    const state = useClipStore.getState()
    expect(state.error).toBe('Fetch clips failed: 500')
    expect(state.isLoading).toBe(false)
  })

  it('createClip sets error state on API failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'out_point must be > in_point' }), { status: 422 }),
    )

    await expect(
      useClipStore.getState().createClip('proj-1', {
        source_video_id: 'vid-1',
        in_point: 100,
        out_point: 50,
        timeline_position: 0,
      }),
    ).rejects.toThrow()

    const state = useClipStore.getState()
    expect(state.error).toBe('out_point must be > in_point')
    expect(state.isLoading).toBe(false)
  })
})
