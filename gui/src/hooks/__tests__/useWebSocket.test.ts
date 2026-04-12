import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useWebSocket } from '../useWebSocket'
import {
  MockWebSocket,
  mockInstances,
  resetMockInstances,
} from '../../__tests__/mockWebSocket'

beforeEach(() => {
  resetMockInstances()
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

  it('delivers all messages in a burst without loss (FR-001, FR-002)', async () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost/ws'))

    act(() => {
      mockInstances[0].simulateOpen()
    })

    // Simulate 10 messages outside of act — all push to queueRef before any render
    for (let i = 0; i < 10; i++) {
      mockInstances[0].simulateMessage(`msg-${i}`)
    }
    // No-op act flushes all pending React state updates and effects
    await act(async () => {})

    expect(result.current.messages).toHaveLength(10)
    expect(result.current.messages[0].data).toBe('msg-0')
    expect(result.current.messages[9].data).toBe('msg-9')
    expect(result.current.lastMessage?.data).toBe('msg-9')
  })

  it('lastMessage equals messages.at(-1) for backward compatibility (FR-003)', async () => {
    const { result } = renderHook(() => useWebSocket('ws://localhost/ws'))

    act(() => {
      mockInstances[0].simulateOpen()
    })

    for (let i = 0; i < 3; i++) {
      mockInstances[0].simulateMessage(`msg-${i}`)
    }
    await act(async () => {})

    const { messages, lastMessage } = result.current
    expect(messages.length).toBeGreaterThan(0)
    expect(lastMessage).toBe(messages.at(-1))
  })
})
