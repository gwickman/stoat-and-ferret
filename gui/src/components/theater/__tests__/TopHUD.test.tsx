import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import TopHUD from '../TopHUD'
import { useProjectStore } from '../../../stores/projectStore'
import type { ConnectionState } from '../../../hooks/useWebSocket'

let mockLastMessage: MessageEvent | null = null
let mockWsState: ConnectionState = 'connected'

vi.mock('../../../hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    state: mockWsState,
    send: vi.fn(),
    lastMessage: mockLastMessage,
  }),
}))

vi.mock('../../../hooks/useProjects', () => ({
  useProjects: () => ({
    projects: [
      { id: 'proj-1', name: 'My Film' },
      { id: 'proj-2', name: 'Other Project' },
    ],
    total: 2,
    loading: false,
    error: null,
    refetch: vi.fn(),
  }),
}))

beforeEach(() => {
  vi.restoreAllMocks()
  mockLastMessage = null
  mockWsState = 'connected'
  useProjectStore.setState({ selectedProjectId: 'proj-1' })
})

describe('TopHUD', () => {
  it('renders the project title', () => {
    render(<TopHUD />)
    expect(screen.getByText('My Film')).toBeDefined()
  })

  it('has the correct data-testid', () => {
    render(<TopHUD />)
    expect(screen.getByTestId('theater-top-hud')).toBeDefined()
  })

  it('shows fallback title when no project is selected', () => {
    useProjectStore.setState({ selectedProjectId: null })
    render(<TopHUD />)
    expect(screen.getByText('Untitled Project')).toBeDefined()
  })

  it('shows fallback title when project ID does not match any project', () => {
    useProjectStore.setState({ selectedProjectId: 'unknown-id' })
    render(<TopHUD />)
    expect(screen.getByText('Untitled Project')).toBeDefined()
  })

  it('displays AI action indicator when AI_ACTION event arrives', () => {
    mockLastMessage = {
      data: JSON.stringify({
        type: 'ai_action',
        payload: { description: 'Analyzing scene composition' },
      }),
    } as MessageEvent

    render(<TopHUD />)
    expect(screen.getByTestId('ai-action-indicator')).toBeDefined()
    expect(screen.getByText('Analyzing scene composition')).toBeDefined()
  })

  it('does not show AI action indicator when no events received', () => {
    render(<TopHUD />)
    expect(screen.queryByTestId('ai-action-indicator')).toBeNull()
  })

  it('does not show AI action indicator when WebSocket is disconnected', () => {
    mockWsState = 'disconnected'
    render(<TopHUD />)
    expect(screen.queryByTestId('ai-action-indicator')).toBeNull()
  })
})
