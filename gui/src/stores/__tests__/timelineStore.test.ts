import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useTimelineStore } from '../timelineStore'

const mockTimeline = {
  project_id: 'proj-1',
  tracks: [
    {
      id: 'track-1',
      project_id: 'proj-1',
      track_type: 'video',
      label: 'Video 1',
      z_index: 0,
      muted: false,
      locked: false,
      clips: [
        {
          id: 'clip-1',
          project_id: 'proj-1',
          source_video_id: 'vid-1',
          track_id: 'track-1',
          timeline_start: 0,
          timeline_end: 10,
          in_point: 0,
          out_point: 300,
        },
      ],
    },
  ],
  duration: 10.0,
  version: 1,
}

beforeEach(() => {
  vi.restoreAllMocks()
  useTimelineStore.getState().reset()
})

describe('timelineStore', () => {
  it('fetchTimeline populates tracks, duration, and version', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify(mockTimeline), { status: 200 }),
    )

    await useTimelineStore.getState().fetchTimeline('proj-1')

    const state = useTimelineStore.getState()
    expect(state.tracks).toHaveLength(1)
    expect(state.tracks[0].id).toBe('track-1')
    expect(state.tracks[0].clips).toHaveLength(1)
    expect(state.duration).toBe(10.0)
    expect(state.version).toBe(1)
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

    const promise = useTimelineStore.getState().fetchTimeline('proj-1')
    expect(useTimelineStore.getState().isLoading).toBe(true)

    resolveFetch!(new Response(JSON.stringify(mockTimeline), { status: 200 }))
    await promise

    expect(useTimelineStore.getState().isLoading).toBe(false)
  })

  it('sets error state on API failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: { message: 'Project not found' } }), { status: 404 }),
    )

    await useTimelineStore.getState().fetchTimeline('bad-id')

    const state = useTimelineStore.getState()
    expect(state.error).toBe('Project not found')
    expect(state.isLoading).toBe(false)
  })

  it('sets error on network failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Network error'))

    await useTimelineStore.getState().fetchTimeline('proj-1')

    const state = useTimelineStore.getState()
    expect(state.error).toBe('Network error')
    expect(state.isLoading).toBe(false)
  })

  it('reset clears all state', () => {
    useTimelineStore.setState({
      tracks: mockTimeline.tracks,
      duration: 10,
      version: 1,
      error: 'some error',
    })

    useTimelineStore.getState().reset()

    const state = useTimelineStore.getState()
    expect(state.tracks).toHaveLength(0)
    expect(state.duration).toBe(0)
    expect(state.version).toBe(0)
    expect(state.error).toBeNull()
    expect(state.isLoading).toBe(false)
  })
})
