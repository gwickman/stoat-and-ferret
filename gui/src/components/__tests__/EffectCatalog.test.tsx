import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import EffectCatalog from '../EffectCatalog'
import type { Effect } from '../../hooks/useEffects'
import { useEffectCatalogStore } from '../../stores/effectCatalogStore'

const mockEffects: Effect[] = [
  {
    effect_type: 'text_overlay',
    name: 'Text Overlay',
    description: 'Add text overlays to video',
    parameter_schema: {},
    ai_hints: { text: 'The text content to overlay' },
    filter_preview: 'drawtext=text=Sample',
  },
  {
    effect_type: 'volume',
    name: 'Volume',
    description: 'Adjust audio volume',
    parameter_schema: {},
    ai_hints: { volume: 'Volume multiplier' },
    filter_preview: 'volume=1.5',
  },
  {
    effect_type: 'xfade',
    name: 'Crossfade (Video)',
    description: 'Crossfade between two video inputs',
    parameter_schema: {},
    ai_hints: { transition: 'Effect type: fade, wipeleft' },
    filter_preview: 'xfade=transition=fade',
  },
]

// Mock the useEffects hook
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
  // Reset store state
  useEffectCatalogStore.setState({
    searchQuery: '',
    selectedCategory: null,
    selectedEffect: null,
    viewMode: 'grid',
  })
})

describe('EffectCatalog', () => {
  it('shows loading state', () => {
    mockUseEffects.mockReturnValue({
      effects: [],
      loading: true,
      error: null,
      refetch: vi.fn(),
    })

    render(<EffectCatalog />)
    expect(screen.getByTestId('effect-catalog-loading')).toBeDefined()
    expect(screen.getByTestId('effect-catalog-loading').textContent).toBe(
      'Loading effects...',
    )
  })

  it('shows error state with retry button', () => {
    const refetch = vi.fn()
    mockUseEffects.mockReturnValue({
      effects: [],
      loading: false,
      error: 'Network error',
      refetch,
    })

    render(<EffectCatalog />)
    expect(screen.getByTestId('effect-catalog-error')).toBeDefined()
    expect(screen.getByText('Network error')).toBeDefined()

    fireEvent.click(screen.getByTestId('effect-catalog-retry'))
    expect(refetch).toHaveBeenCalledTimes(1)
  })

  it('renders effect cards with name, description, and category', () => {
    mockUseEffects.mockReturnValue({
      effects: mockEffects,
      loading: false,
      error: null,
      refetch: vi.fn(),
    })

    render(<EffectCatalog />)

    expect(screen.getByTestId('effect-catalog')).toBeDefined()
    expect(screen.getByTestId('effect-card-text_overlay')).toBeDefined()
    expect(screen.getByTestId('effect-card-volume')).toBeDefined()
    expect(screen.getByTestId('effect-card-xfade')).toBeDefined()

    // Check names are rendered
    expect(screen.getByText('Text Overlay')).toBeDefined()
    expect(screen.getByText('Volume')).toBeDefined()
    expect(screen.getByText('Crossfade (Video)')).toBeDefined()

    // Check descriptions
    expect(screen.getByText('Add text overlays to video')).toBeDefined()
    expect(screen.getByText('Adjust audio volume')).toBeDefined()

    // Check category badges
    const badges = screen.getAllByTestId('effect-category-badge')
    expect(badges.length).toBe(3)
  })

  it('toggles between grid and list view', () => {
    mockUseEffects.mockReturnValue({
      effects: mockEffects,
      loading: false,
      error: null,
      refetch: vi.fn(),
    })

    render(<EffectCatalog />)

    const toggle = screen.getByTestId('effect-view-toggle')
    expect(toggle.textContent).toBe('List')

    fireEvent.click(toggle)
    expect(toggle.textContent).toBe('Grid')

    fireEvent.click(toggle)
    expect(toggle.textContent).toBe('List')
  })

  it('filters effects by search query', () => {
    mockUseEffects.mockReturnValue({
      effects: mockEffects,
      loading: false,
      error: null,
      refetch: vi.fn(),
    })

    render(<EffectCatalog />)

    const input = screen.getByTestId('effect-search-input')
    fireEvent.change(input, { target: { value: 'volume' } })

    expect(screen.getByTestId('effect-card-volume')).toBeDefined()
    expect(screen.queryByTestId('effect-card-text_overlay')).toBeNull()
    expect(screen.queryByTestId('effect-card-xfade')).toBeNull()
  })

  it('filters effects by category', () => {
    mockUseEffects.mockReturnValue({
      effects: mockEffects,
      loading: false,
      error: null,
      refetch: vi.fn(),
    })

    render(<EffectCatalog />)

    const filter = screen.getByTestId('effect-category-filter')
    fireEvent.change(filter, { target: { value: 'audio' } })

    expect(screen.getByTestId('effect-card-volume')).toBeDefined()
    expect(screen.queryByTestId('effect-card-text_overlay')).toBeNull()
    expect(screen.queryByTestId('effect-card-xfade')).toBeNull()
  })

  it('shows empty message when no effects match', () => {
    mockUseEffects.mockReturnValue({
      effects: mockEffects,
      loading: false,
      error: null,
      refetch: vi.fn(),
    })

    render(<EffectCatalog />)

    const input = screen.getByTestId('effect-search-input')
    fireEvent.change(input, { target: { value: 'nonexistent' } })

    expect(screen.getByTestId('effect-catalog-empty')).toBeDefined()
  })

  it('shows AI hint tooltip via title attribute', () => {
    mockUseEffects.mockReturnValue({
      effects: mockEffects,
      loading: false,
      error: null,
      refetch: vi.fn(),
    })

    render(<EffectCatalog />)

    const card = screen.getByTestId('effect-card-text_overlay')
    expect(card.getAttribute('title')).toBe('The text content to overlay')
  })

  it('selects an effect on click', () => {
    mockUseEffects.mockReturnValue({
      effects: mockEffects,
      loading: false,
      error: null,
      refetch: vi.fn(),
    })

    render(<EffectCatalog />)

    fireEvent.click(screen.getByTestId('effect-card-volume'))

    expect(useEffectCatalogStore.getState().selectedEffect).toBe('volume')
  })

  it('combines search and category filter', () => {
    mockUseEffects.mockReturnValue({
      effects: mockEffects,
      loading: false,
      error: null,
      refetch: vi.fn(),
    })

    render(<EffectCatalog />)

    // Filter by video category first
    const filter = screen.getByTestId('effect-category-filter')
    fireEvent.change(filter, { target: { value: 'video' } })

    // Then search for 'text'
    const input = screen.getByTestId('effect-search-input')
    fireEvent.change(input, { target: { value: 'text' } })

    expect(screen.getByTestId('effect-card-text_overlay')).toBeDefined()
    expect(screen.queryByTestId('effect-card-volume')).toBeNull()
    expect(screen.queryByTestId('effect-card-xfade')).toBeNull()
  })
})
