import { render, screen, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

// HLS.js mock — the factory is hoisted, so we use vi.hoisted() to define
// shared state that both the factory and the tests can reference.
const { mockInstance, MockHls, constructorSpy } = vi.hoisted(() => {
  const mockInstance = {
    loadSource: vi.fn(),
    attachMedia: vi.fn(),
    destroy: vi.fn(),
    recoverMediaError: vi.fn(),
    startLoad: vi.fn(),
    on: vi.fn(),
    config: {},
  }

  const constructorSpy = vi.fn()

  // Must be a real function (not arrow) so `new` works
  function MockHls(config: Record<string, unknown>) {
    constructorSpy(config)
    return mockInstance
  }

  MockHls.isSupported = vi.fn(() => true)
  MockHls.Events = {
    ERROR: 'hlsError',
    MANIFEST_PARSED: 'hlsManifestParsed',
  }
  MockHls.ErrorTypes = {
    MEDIA_ERROR: 'mediaError',
    NETWORK_ERROR: 'networkError',
    OTHER_ERROR: 'otherError',
  }

  return { mockInstance, MockHls, constructorSpy }
})

vi.mock('hls.js', () => ({
  default: MockHls,
}))

import PreviewPlayer from '../PreviewPlayer'

beforeEach(() => {
  vi.clearAllMocks()
  ;(MockHls.isSupported as ReturnType<typeof vi.fn>).mockReturnValue(true)
})

describe('PreviewPlayer', () => {
  it('renders video element with correct data-testid', () => {
    render(<PreviewPlayer manifestUrl="/api/v1/preview/test/manifest.m3u8" />)

    expect(screen.getByTestId('preview-player-video')).toBeDefined()
    expect(screen.getByTestId('preview-player-container')).toBeDefined()
  })

  it('shows loading indicator when manifest URL is null', () => {
    render(<PreviewPlayer manifestUrl={null} />)

    expect(screen.getByTestId('preview-player-loading')).toBeDefined()
    expect(screen.queryByTestId('preview-player-video')).toBeNull()
  })

  it('shows loading indicator when manifest URL is undefined', () => {
    render(<PreviewPlayer manifestUrl={undefined} />)

    expect(screen.getByTestId('preview-player-loading')).toBeDefined()
  })

  it('initializes HLS.js with correct VOD config', () => {
    render(<PreviewPlayer manifestUrl="/api/v1/preview/test/manifest.m3u8" />)

    expect(constructorSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        lowLatencyMode: false,
        startPosition: -1,
        maxBufferLength: 30,
        enableWorker: true,
      }),
    )
  })

  it('loads source and attaches media on mount', () => {
    render(<PreviewPlayer manifestUrl="/api/v1/preview/test/manifest.m3u8" />)

    expect(mockInstance.loadSource).toHaveBeenCalledWith(
      '/api/v1/preview/test/manifest.m3u8',
    )
    expect(mockInstance.attachMedia).toHaveBeenCalled()
  })

  it('registers error handler', () => {
    render(<PreviewPlayer manifestUrl="/api/v1/preview/test/manifest.m3u8" />)

    expect(mockInstance.on).toHaveBeenCalledWith('hlsError', expect.any(Function))
  })

  it('calls destroy() on unmount', () => {
    const { unmount } = render(
      <PreviewPlayer manifestUrl="/api/v1/preview/test/manifest.m3u8" />,
    )

    unmount()

    expect(mockInstance.destroy).toHaveBeenCalled()
  })

  describe('error recovery', () => {
    function getErrorHandler(): (event: string, data: { fatal: boolean; type: string; details: string }) => void {
      const call = mockInstance.on.mock.calls.find(
        (c: unknown[]) => c[0] === 'hlsError',
      )
      return call![1] as (event: string, data: { fatal: boolean; type: string; details: string }) => void
    }

    it('recovers from MEDIA_ERROR with recoverMediaError()', () => {
      render(<PreviewPlayer manifestUrl="/api/v1/preview/test/manifest.m3u8" />)

      const handler = getErrorHandler()
      act(() => {
        handler('hlsError', {
          fatal: true,
          type: 'mediaError',
          details: 'bufferStalledError',
        })
      })

      expect(mockInstance.recoverMediaError).toHaveBeenCalled()
    })

    it('recovers from NETWORK_ERROR with startLoad()', () => {
      render(<PreviewPlayer manifestUrl="/api/v1/preview/test/manifest.m3u8" />)

      const handler = getErrorHandler()
      act(() => {
        handler('hlsError', {
          fatal: true,
          type: 'networkError',
          details: 'manifestLoadError',
        })
      })

      expect(mockInstance.startLoad).toHaveBeenCalledWith(-1)
    })

    it('destroys on other fatal errors and reports error', () => {
      const onError = vi.fn()
      render(
        <PreviewPlayer
          manifestUrl="/api/v1/preview/test/manifest.m3u8"
          onError={onError}
        />,
      )

      const handler = getErrorHandler()
      act(() => {
        handler('hlsError', {
          fatal: true,
          type: 'otherError',
          details: 'internalException',
        })
      })

      expect(mockInstance.destroy).toHaveBeenCalled()
      expect(onError).toHaveBeenCalledWith(
        'Fatal playback error: internalException',
      )
    })

    it('ignores non-fatal errors', () => {
      render(<PreviewPlayer manifestUrl="/api/v1/preview/test/manifest.m3u8" />)

      const handler = getErrorHandler()
      act(() => {
        handler('hlsError', {
          fatal: false,
          type: 'networkError',
          details: 'fragLoadError',
        })
      })

      expect(mockInstance.recoverMediaError).not.toHaveBeenCalled()
      expect(mockInstance.startLoad).not.toHaveBeenCalled()
    })
  })

  describe('Safari native fallback', () => {
    beforeEach(() => {
      ;(MockHls.isSupported as ReturnType<typeof vi.fn>).mockReturnValue(false)
    })

    it('uses native video.src when Hls.isSupported() is false', () => {
      const spy = vi
        .spyOn(HTMLVideoElement.prototype, 'canPlayType')
        .mockReturnValue('maybe')

      render(<PreviewPlayer manifestUrl="/api/v1/preview/test/manifest.m3u8" />)

      const video = screen.getByTestId('preview-player-video') as HTMLVideoElement
      expect(video.src).toContain('/api/v1/preview/test/manifest.m3u8')

      spy.mockRestore()
    })

    it('cleans up video src on unmount in Safari path', () => {
      const spy = vi
        .spyOn(HTMLVideoElement.prototype, 'canPlayType')
        .mockReturnValue('maybe')

      const { unmount } = render(
        <PreviewPlayer manifestUrl="/api/v1/preview/test/manifest.m3u8" />,
      )

      const video = screen.getByTestId('preview-player-video') as HTMLVideoElement
      unmount()

      expect(video.getAttribute('src')).toBeNull()

      spy.mockRestore()
    })

    it('reports error when neither HLS.js nor native is supported', () => {
      const spy = vi
        .spyOn(HTMLVideoElement.prototype, 'canPlayType')
        .mockReturnValue('')
      const onError = vi.fn()

      render(
        <PreviewPlayer
          manifestUrl="/api/v1/preview/test/manifest.m3u8"
          onError={onError}
        />,
      )

      expect(onError).toHaveBeenCalledWith(
        'HLS playback not supported in this browser',
      )

      spy.mockRestore()
    })
  })

  describe('parity: HLS.js vs Safari', () => {
    it('both paths render the same video element', () => {
      // HLS.js path
      ;(MockHls.isSupported as ReturnType<typeof vi.fn>).mockReturnValue(true)
      const { unmount: unmount1 } = render(
        <PreviewPlayer manifestUrl="/api/v1/preview/test/manifest.m3u8" />,
      )
      expect(screen.getByTestId('preview-player-video')).toBeDefined()
      unmount1()

      // Safari path
      ;(MockHls.isSupported as ReturnType<typeof vi.fn>).mockReturnValue(false)
      const spy = vi
        .spyOn(HTMLVideoElement.prototype, 'canPlayType')
        .mockReturnValue('maybe')

      render(<PreviewPlayer manifestUrl="/api/v1/preview/test/manifest.m3u8" />)
      expect(screen.getByTestId('preview-player-video')).toBeDefined()

      spy.mockRestore()
    })

    it('both paths clean up on unmount', () => {
      // HLS.js path cleanup
      ;(MockHls.isSupported as ReturnType<typeof vi.fn>).mockReturnValue(true)
      const { unmount: unmount1 } = render(
        <PreviewPlayer manifestUrl="/api/v1/preview/test/manifest.m3u8" />,
      )
      unmount1()
      expect(mockInstance.destroy).toHaveBeenCalled()

      vi.clearAllMocks()

      // Safari path cleanup
      ;(MockHls.isSupported as ReturnType<typeof vi.fn>).mockReturnValue(false)
      const spy = vi
        .spyOn(HTMLVideoElement.prototype, 'canPlayType')
        .mockReturnValue('maybe')

      const { unmount: unmount2 } = render(
        <PreviewPlayer manifestUrl="/api/v1/preview/test/manifest.m3u8" />,
      )
      const video = screen.getByTestId('preview-player-video') as HTMLVideoElement
      unmount2()
      expect(video.getAttribute('src')).toBeNull()

      spy.mockRestore()
    })
  })

  describe('buffer tracking', () => {
    it('calls onBufferUpdate on progress events', () => {
      const onBufferUpdate = vi.fn()

      render(
        <PreviewPlayer
          manifestUrl="/api/v1/preview/test/manifest.m3u8"
          onBufferUpdate={onBufferUpdate}
        />,
      )

      const video = screen.getByTestId('preview-player-video') as HTMLVideoElement

      // Simulate buffered TimeRanges
      Object.defineProperty(video, 'buffered', {
        value: {
          length: 1,
          start: (i: number) => (i === 0 ? 0 : 0),
          end: (i: number) => (i === 0 ? 10 : 0),
        },
        configurable: true,
      })

      act(() => {
        video.dispatchEvent(new Event('progress'))
      })

      expect(onBufferUpdate).toHaveBeenCalledWith([{ start: 0, end: 10 }])
    })
  })
})
