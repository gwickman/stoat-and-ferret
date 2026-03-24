/**
 * Shared MockWebSocket utility for tests that need to simulate WebSocket connections.
 */

export let mockInstances: MockWebSocket[]

export class MockWebSocket {
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

export function resetMockInstances() {
  mockInstances = []
}

/**
 * Create a WebSocket message event with JSON-serialized data.
 */
export function makeMessage(data: object): MessageEvent {
  return new MessageEvent('message', { data: JSON.stringify(data) })
}
