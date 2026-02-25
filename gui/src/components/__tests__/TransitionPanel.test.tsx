import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import TransitionPanel from '../TransitionPanel'
import type { Clip } from '../../hooks/useProjects'
import type { Effect } from '../../hooks/useEffects'
import { useTransitionStore } from '../../stores/transitionStore'
import { useEffectFormStore } from '../../stores/effectFormStore'

const mockClips: Clip[] = [
  {
    id: 'clip-1',
    project_id: 'proj-1',
    source_video_id: 'video-1',
    in_point: 0,
    out_point: 100,
    timeline_position: 0,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'clip-2',
    project_id: 'proj-1',
    source_video_id: 'video-2',
    in_point: 50,
    out_point: 200,
    timeline_position: 100,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
]

const mockTransitionEffects: Effect[] = [
  {
    effect_type: 'xfade',
    name: 'Crossfade (Video)',
    description: 'Video crossfade transition',
    parameter_schema: {
      type: 'object',
      properties: {
        duration: { type: 'number', minimum: 0, maximum: 10, default: 1, description: 'Duration in seconds' },
      },
    },
    ai_hints: { transition: 'fade' },
    filter_preview: 'xfade=transition=fade',
  },
  {
    effect_type: 'acrossfade',
    name: 'Crossfade (Audio)',
    description: 'Audio crossfade transition',
    parameter_schema: {
      type: 'object',
      properties: {
        duration: { type: 'number', minimum: 0, maximum: 10, default: 1 },
      },
    },
    ai_hints: { transition: 'acrossfade' },
    filter_preview: 'acrossfade=d=1',
  },
]

const mockAllEffects: Effect[] = [
  {
    effect_type: 'text_overlay',
    name: 'Text Overlay',
    description: 'Add text overlays',
    parameter_schema: {},
    ai_hints: {},
    filter_preview: 'drawtext=text=hello',
  },
  ...mockTransitionEffects,
]

vi.mock('../../hooks/useEffects', async () => {
  const actual = await vi.importActual('../../hooks/useEffects')
  return {
    ...actual,
    useEffects: vi.fn(),
  }
})

import { useEffects } from '../../hooks/useEffects'
const mockUseEffects = vi.mocked(useEffects)

beforeEach(() => {
  vi.restoreAllMocks()
  useTransitionStore.getState().reset()
  useEffectFormStore.getState().resetForm()
  mockUseEffects.mockReturnValue({
    effects: mockAllEffects,
    loading: false,
    error: null,
    refetch: vi.fn(),
  })
})

describe('TransitionPanel', () => {
  it('renders clip selector in pair-mode', () => {
    render(<TransitionPanel projectId="proj-1" clips={mockClips} />)

    expect(screen.getByTestId('transition-panel')).toBeDefined()
    expect(screen.getByText('Select Clip Pair')).toBeDefined()
  })

  it('shows transition type catalog', () => {
    render(<TransitionPanel projectId="proj-1" clips={mockClips} />)

    expect(screen.getByTestId('transition-catalog')).toBeDefined()
    expect(screen.getByTestId('transition-type-xfade')).toBeDefined()
    expect(screen.getByTestId('transition-type-acrossfade')).toBeDefined()
  })

  it('does not show non-transition effects in catalog', () => {
    render(<TransitionPanel projectId="proj-1" clips={mockClips} />)

    expect(screen.queryByTestId('transition-type-text_overlay')).toBeNull()
  })

  it('selects a transition type and shows parameter form', () => {
    render(<TransitionPanel projectId="proj-1" clips={mockClips} />)

    fireEvent.click(screen.getByTestId('transition-type-xfade'))

    // Parameter form should be rendered
    expect(screen.getByTestId('effect-parameter-form')).toBeDefined()
  })

  it('shows apply button when both clips and transition type selected', () => {
    // Pre-set store state
    useTransitionStore.getState().selectSource('clip-1')
    useTransitionStore.getState().selectTarget('clip-2')

    render(<TransitionPanel projectId="proj-1" clips={mockClips} />)

    fireEvent.click(screen.getByTestId('transition-type-xfade'))

    expect(screen.getByTestId('apply-transition-btn')).toBeDefined()
  })

  it('does not show apply button when clips not fully selected', () => {
    useTransitionStore.getState().selectSource('clip-1')
    // No target selected

    render(<TransitionPanel projectId="proj-1" clips={mockClips} />)

    fireEvent.click(screen.getByTestId('transition-type-xfade'))

    expect(screen.queryByTestId('apply-transition-btn')).toBeNull()
  })

  it('submits transition via POST endpoint', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    })
    globalThis.fetch = mockFetch

    useTransitionStore.getState().selectSource('clip-1')
    useTransitionStore.getState().selectTarget('clip-2')

    render(<TransitionPanel projectId="proj-1" clips={mockClips} />)

    fireEvent.click(screen.getByTestId('transition-type-xfade'))
    fireEvent.click(screen.getByTestId('apply-transition-btn'))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/projects/proj-1/effects/transition',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    })
  })

  it('shows error for non-adjacent clips', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: () => Promise.resolve({ detail: { message: 'Clips are not adjacent' } }),
    })
    globalThis.fetch = mockFetch

    useTransitionStore.getState().selectSource('clip-1')
    useTransitionStore.getState().selectTarget('clip-2')

    render(<TransitionPanel projectId="proj-1" clips={mockClips} />)

    fireEvent.click(screen.getByTestId('transition-type-xfade'))
    fireEvent.click(screen.getByTestId('apply-transition-btn'))

    await waitFor(() => {
      const status = screen.getByTestId('transition-status')
      expect(status.textContent).toContain('not adjacent')
    })
  })

  it('shows reset button when both clips selected', () => {
    useTransitionStore.getState().selectSource('clip-1')
    useTransitionStore.getState().selectTarget('clip-2')

    render(<TransitionPanel projectId="proj-1" clips={mockClips} />)

    expect(screen.getByTestId('reset-pair-btn')).toBeDefined()
  })

  it('shows empty message when no transition effects available', () => {
    mockUseEffects.mockReturnValue({
      effects: [mockAllEffects[0]], // only text_overlay
      loading: false,
      error: null,
      refetch: vi.fn(),
    })

    render(<TransitionPanel projectId="proj-1" clips={mockClips} />)

    expect(screen.getByTestId('transition-catalog-empty')).toBeDefined()
  })
})
