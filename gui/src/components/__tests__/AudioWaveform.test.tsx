import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import AudioWaveform from '../AudioWaveform'

const mockObjectUrl = 'blob:http://localhost/fake-waveform'

beforeEach(() => {
  vi.spyOn(URL, 'createObjectURL').mockReturnValue(mockObjectUrl)
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('AudioWaveform', () => {
  it('renders waveform PNG as background-image on success', async () => {
    const blob = new Blob(['png-data'], { type: 'image/png' })
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(blob, { status: 200 }),
    )

    render(<AudioWaveform videoId="vid-1" />)

    await waitFor(() => {
      expect(screen.getByTestId('audio-waveform')).toBeDefined()
    })

    const el = screen.getByTestId('audio-waveform')
    expect(el.style.backgroundImage).toContain(mockObjectUrl)
    expect(el.style.backgroundSize).toBe('100% 100%')
  })

  it('shows placeholder when waveform is not generated (fetch fails)', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('', { status: 404 }),
    )

    render(<AudioWaveform videoId="vid-1" />)

    await waitFor(() => {
      expect(screen.getByTestId('audio-waveform')).toBeDefined()
    })

    const el = screen.getByTestId('audio-waveform')
    expect(el.style.backgroundImage).toContain('linear-gradient')
  })

  it('shows placeholder when fetch rejects', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Network error'))

    render(<AudioWaveform videoId="vid-1" />)

    await waitFor(() => {
      expect(screen.getByTestId('audio-waveform')).toBeDefined()
    })

    const el = screen.getByTestId('audio-waveform')
    expect(el.style.background).toContain('linear-gradient')
  })

  it('scales to fit clip width via background-size 100% 100%', async () => {
    const blob = new Blob(['png-data'], { type: 'image/png' })
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(blob, { status: 200 }),
    )

    render(<AudioWaveform videoId="vid-1" />)

    await waitFor(() => {
      expect(screen.getByTestId('audio-waveform')).toBeDefined()
    })

    const el = screen.getByTestId('audio-waveform')
    expect(el.style.backgroundSize).toBe('100% 100%')
    expect(el.style.backgroundRepeat).toBe('no-repeat')
  })

  it('does not block timeline rendering during async load', () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => {}))

    render(
      <div data-testid="timeline">
        <AudioWaveform videoId="vid-1" />
        <span data-testid="other-content">visible</span>
      </div>,
    )

    expect(screen.getByTestId('other-content')).toBeDefined()
    expect(screen.queryByTestId('audio-waveform')).toBeNull()
  })

  it('fetches from correct API endpoint', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(new Blob(), { status: 200 }),
    )

    render(<AudioWaveform videoId="my-video-123" />)

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith('/api/v1/videos/my-video-123/waveform.png')
    })
  })

  it('uses pointer-events-none so clicks pass through to clip', async () => {
    const blob = new Blob(['png-data'], { type: 'image/png' })
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(blob, { status: 200 }),
    )

    render(<AudioWaveform videoId="vid-1" />)

    await waitFor(() => {
      expect(screen.getByTestId('audio-waveform')).toBeDefined()
    })

    const el = screen.getByTestId('audio-waveform')
    expect(el.className).toContain('pointer-events-none')
  })
})
