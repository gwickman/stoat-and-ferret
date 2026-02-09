import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import StatusBar from '../StatusBar'

describe('StatusBar', () => {
  it('shows connected state', () => {
    render(<StatusBar connectionState="connected" />)
    expect(screen.getByText('WebSocket: Connected')).toBeDefined()
  })

  it('shows disconnected state', () => {
    render(<StatusBar connectionState="disconnected" />)
    expect(screen.getByText('WebSocket: Disconnected')).toBeDefined()
  })

  it('shows reconnecting state', () => {
    render(<StatusBar connectionState="reconnecting" />)
    expect(screen.getByText('WebSocket: Reconnecting...')).toBeDefined()
  })
})
