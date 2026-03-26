import { describe, it, expect, vi, beforeEach } from 'vitest'
import { usePreviewStore } from '../previewStore'

beforeEach(() => {
  vi.restoreAllMocks()
  usePreviewStore.getState().reset()
})

describe('previewStore', () => {
  it('initializes with correct defaults', () => {
    const state = usePreviewStore.getState()
    expect(state.sessionId).toBeNull()
    expect(state.status).toBeNull()
    expect(state.quality).toBe('medium')
    expect(state.position).toBe(0)
    expect(state.duration).toBe(0)
    expect(state.volume).toBe(1.0)
    expect(state.muted).toBe(false)
    expect(state.progress).toBe(0)
    expect(state.error).toBeNull()
  })

  describe('connect', () => {
    it('sets sessionId and status on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ session_id: 'sess-1' }), { status: 202 }),
      )

      await usePreviewStore.getState().connect('proj-1')

      const state = usePreviewStore.getState()
      expect(state.sessionId).toBe('sess-1')
      expect(state.status).toBe('generating')
      expect(state.error).toBeNull()
    })

    it('sends correct request body with quality', async () => {
      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ session_id: 'sess-1' }), { status: 202 }),
      )

      await usePreviewStore.getState().connect('proj-1')

      const [url, opts] = fetchSpy.mock.calls[0]
      expect(url).toBe('/api/v1/projects/proj-1/preview/start')
      expect(opts?.method).toBe('POST')
      expect(JSON.parse(opts?.body as string)).toEqual({ quality: 'medium' })
    })

    it('sets error status on API failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'Project not found' }), { status: 404 }),
      )

      await usePreviewStore.getState().connect('proj-1')

      const state = usePreviewStore.getState()
      expect(state.status).toBe('error')
      expect(state.error).toBe('Project not found')
      expect(state.sessionId).toBeNull()
    })

    it('sets error status on network failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Network error'))

      await usePreviewStore.getState().connect('proj-1')

      const state = usePreviewStore.getState()
      expect(state.status).toBe('error')
      expect(state.error).toBe('Network error')
    })
  })

  describe('disconnect', () => {
    it('resets all state to defaults', async () => {
      // Set some state first
      usePreviewStore.setState({
        sessionId: 'sess-1',
        status: 'ready',
        position: 10,
        duration: 60,
        progress: 0.5,
      })

      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response('', { status: 200 }),
      )

      usePreviewStore.getState().disconnect()

      const state = usePreviewStore.getState()
      expect(state.sessionId).toBeNull()
      expect(state.status).toBeNull()
      expect(state.position).toBe(0)
      expect(state.duration).toBe(0)
      expect(state.progress).toBe(0)
    })

    it('calls DELETE endpoint for active session', () => {
      usePreviewStore.setState({ sessionId: 'sess-1' })

      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        new Response('', { status: 200 }),
      )

      usePreviewStore.getState().disconnect()

      expect(fetchSpy).toHaveBeenCalledWith('/api/v1/preview/sess-1', { method: 'DELETE' })
    })
  })

  describe('setQuality', () => {
    it('creates new session with new quality', async () => {
      usePreviewStore.setState({ sessionId: 'sess-1', status: 'ready' })

      const fetchSpy = vi.spyOn(globalThis, 'fetch')
      // DELETE old session
      fetchSpy.mockResolvedValueOnce(new Response('', { status: 200 }))
      // POST new session
      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify({ session_id: 'sess-2' }), { status: 202 }),
      )

      await usePreviewStore.getState().setQuality('proj-1', 'high')

      const state = usePreviewStore.getState()
      expect(state.quality).toBe('high')
      expect(state.sessionId).toBe('sess-2')
      expect(state.status).toBe('generating')
    })

    it('rejects invalid quality values', async () => {
      usePreviewStore.setState({ quality: 'medium' })

      await usePreviewStore.getState().setQuality('proj-1', 'ultra' as 'high')

      expect(usePreviewStore.getState().quality).toBe('medium')
    })
  })

  describe('setVolume', () => {
    it('sets volume within valid range', () => {
      usePreviewStore.getState().setVolume(0.5)
      expect(usePreviewStore.getState().volume).toBe(0.5)
    })

    it('clamps volume to minimum 0', () => {
      usePreviewStore.getState().setVolume(-0.5)
      expect(usePreviewStore.getState().volume).toBe(0)
    })

    it('clamps volume to maximum 1', () => {
      usePreviewStore.getState().setVolume(1.5)
      expect(usePreviewStore.getState().volume).toBe(1)
    })
  })

  describe('setMuted', () => {
    it('sets muted state', () => {
      usePreviewStore.getState().setMuted(true)
      expect(usePreviewStore.getState().muted).toBe(true)

      usePreviewStore.getState().setMuted(false)
      expect(usePreviewStore.getState().muted).toBe(false)
    })
  })

  describe('setPosition', () => {
    it('sets position within valid range', () => {
      usePreviewStore.setState({ duration: 60 })
      usePreviewStore.getState().setPosition(30)
      expect(usePreviewStore.getState().position).toBe(30)
    })

    it('clamps position to duration', () => {
      usePreviewStore.setState({ duration: 60 })
      usePreviewStore.getState().setPosition(100)
      expect(usePreviewStore.getState().position).toBe(60)
    })

    it('clamps position to minimum 0', () => {
      usePreviewStore.setState({ duration: 60 })
      usePreviewStore.getState().setPosition(-10)
      expect(usePreviewStore.getState().position).toBe(0)
    })
  })

  describe('setProgress', () => {
    it('sets progress within valid range', () => {
      usePreviewStore.getState().setProgress(0.5)
      expect(usePreviewStore.getState().progress).toBe(0.5)
    })

    it('clamps progress to [0, 1]', () => {
      usePreviewStore.getState().setProgress(1.5)
      expect(usePreviewStore.getState().progress).toBe(1)

      usePreviewStore.getState().setProgress(-0.5)
      expect(usePreviewStore.getState().progress).toBe(0)
    })
  })

  describe('setError', () => {
    it('sets and clears error', () => {
      usePreviewStore.getState().setError('Something went wrong')
      expect(usePreviewStore.getState().error).toBe('Something went wrong')

      usePreviewStore.getState().setError(null)
      expect(usePreviewStore.getState().error).toBeNull()
    })
  })

  describe('reset', () => {
    it('resets all state to initial values', () => {
      usePreviewStore.setState({
        sessionId: 'sess-1',
        status: 'ready',
        quality: 'high',
        position: 30,
        duration: 60,
        volume: 0.5,
        muted: true,
        progress: 1.0,
        error: 'some error',
      })

      usePreviewStore.getState().reset()

      const state = usePreviewStore.getState()
      expect(state.sessionId).toBeNull()
      expect(state.status).toBeNull()
      expect(state.quality).toBe('medium')
      expect(state.position).toBe(0)
      expect(state.duration).toBe(0)
      expect(state.volume).toBe(1.0)
      expect(state.muted).toBe(false)
      expect(state.progress).toBe(0)
      expect(state.error).toBeNull()
    })
  })
})
