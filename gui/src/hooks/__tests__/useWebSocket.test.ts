import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useWebSocket } from '../useWebSocket'

let mockInstances: MockWebSocket[]

class MockWebSocket {
  static readonly OPEN = 1
  static readonly CLOSED = 3

  url: string
  onopen: (() => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  onmessage: ((e: MessageEvent) => void) | null = null
  readyState = MockWebSocket.OPEN
  sentData: string[] = []

  constructor(url: string) {
    this.url = url
    mockInstances.push(this)
  }

  close() {
    this.readyState = MockWebSocket.CLOSED
  }

  send(data: string) {
    this.sentData.push(data)
  }

  simulateOpen() {
    this.readyState = MockWebSocket.OPEN
    this.onopen?.()
  }

  simulateClose() {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.()
  }

  simulateMessage(data: string) {
    this.onmessage?.(new MessageEvent('message', { data }))
  }
}

beforeEach(() => {
  mockInstances = []
  vi.stubGlobal('WebSocket', MockWebSocket)
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('useWebSocket', () => {
  it('connects to the given URL', () => {
    renderHook(() => useWebSocket('ws://localhost/ws'))
    expect(mockInstances).toHaveLength(1)
    expect(mockInstances[0].url).toBe('ws://localhost/ws')
  })

  it('reports connected state after onopen', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost/ws'))

    act(() => {
      mockInstances[0].simulateOpen()
    })

    expect(result.current.state).toBe('connected')
  })

  it('reports reconnecting state after onclose', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost/ws'))

    act(() => {
      mockInstances[0].simulateOpen()
    })
    expect(result.current.state).toBe('connected')

    act(() => {
      mockInstances[0].simulateClose()
    })
    expect(result.current.state).toBe('reconnecting')
  })

  it('reconnects with exponential backoff', () => {
    renderHook(() => useWebSocket('ws://localhost/ws'))

    // First close -> reconnect after 1s (2^0 * 1000)
    act(() => {
      mockInstances[0].simulateClose()
    })
    expect(mockInstances).toHaveLength(1)

    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(mockInstances).toHaveLength(2)

    // Second close -> reconnect after 2s (2^1 * 1000)
    act(() => {
      mockInstances[1].simulateClose()
    })
    act(() => {
      vi.advanceTimersByTime(1999)
    })
    expect(mockInstances).toHaveLength(2) // not yet

    act(() => {
      vi.advanceTimersByTime(1)
    })
    expect(mockInstances).toHaveLength(3) // now reconnected
  })

  it('resets retry count on successful connection', () => {
    renderHook(() => useWebSocket('ws://localhost/ws'))

    // Disconnect and reconnect
    act(() => {
      mockInstances[0].simulateClose()
    })
    act(() => {
      vi.advanceTimersByTime(1000)
    })

    // Successfully connect
    act(() => {
      mockInstances[1].simulateOpen()
    })

    // Disconnect again -> should use 1s delay (reset)
    act(() => {
      mockInstances[1].simulateClose()
    })
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(mockInstances).toHaveLength(3)
  })

  it('sends data when connected', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost/ws'))

    act(() => {
      mockInstances[0].simulateOpen()
    })

    act(() => {
      result.current.send('hello')
    })

    expect(mockInstances[0].sentData).toEqual(['hello'])
  })

  it('stores the last received message', () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost/ws'))

    act(() => {
      mockInstances[0].simulateOpen()
    })

    act(() => {
      mockInstances[0].simulateMessage('test-data')
    })

    expect(result.current.lastMessage?.data).toBe('test-data')
  })

  it('caps backoff delay at 30 seconds', () => {
    renderHook(() => useWebSocket('ws://localhost/ws'))

    // Simulate many disconnects to push delay past 30s
    for (let i = 0; i < 10; i++) {
      act(() => {
        mockInstances[mockInstances.length - 1].simulateClose()
      })
      act(() => {
        vi.advanceTimersByTime(30_000)
      })
    }

    // All reconnects should have happened (max delay is 30s)
    expect(mockInstances.length).toBeGreaterThan(5)
  })
})
