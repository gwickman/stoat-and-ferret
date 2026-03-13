import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import LayoutSelector from '../LayoutSelector'
import { useComposeStore } from '../../stores/composeStore'

const ALL_PRESETS = [
  { name: 'PipTopLeft', description: 'PIP top-left overlay', ai_hint: '', min_inputs: 2, max_inputs: 2 },
  { name: 'PipTopRight', description: 'PIP top-right overlay', ai_hint: '', min_inputs: 2, max_inputs: 2 },
  { name: 'PipBottomLeft', description: 'PIP bottom-left overlay', ai_hint: '', min_inputs: 2, max_inputs: 2 },
  { name: 'PipBottomRight', description: 'PIP bottom-right overlay', ai_hint: '', min_inputs: 2, max_inputs: 2 },
  { name: 'SideBySide', description: 'Side-by-side split', ai_hint: '', min_inputs: 2, max_inputs: 2 },
  { name: 'TopBottom', description: 'Top-bottom split', ai_hint: '', min_inputs: 2, max_inputs: 2 },
  { name: 'Grid2x2', description: '2x2 grid layout', ai_hint: '', min_inputs: 2, max_inputs: 4 },
]

beforeEach(() => {
  useComposeStore.getState().reset()
})

describe('LayoutSelector', () => {
  it('renders nothing when no presets are available', () => {
    const { container } = render(<LayoutSelector />)
    expect(container.innerHTML).toBe('')
  })

  it('renders all 7 presets as selectable items', () => {
    useComposeStore.setState({ presets: ALL_PRESETS })

    render(<LayoutSelector />)

    expect(screen.getByTestId('layout-selector')).toBeDefined()
    for (const preset of ALL_PRESETS) {
      expect(screen.getByTestId(`preset-${preset.name}`)).toBeDefined()
      expect(screen.getByText(preset.name)).toBeDefined()
    }
  })

  it('shows description for each preset', () => {
    useComposeStore.setState({ presets: ALL_PRESETS })

    render(<LayoutSelector />)

    for (const preset of ALL_PRESETS) {
      expect(screen.getByText(preset.description)).toBeDefined()
    }
  })

  it('highlights the selected preset', () => {
    useComposeStore.setState({ presets: ALL_PRESETS, selectedPreset: 'SideBySide' })

    render(<LayoutSelector />)

    const selected = screen.getByTestId('preset-SideBySide')
    expect(selected.className).toContain('border-blue-500')

    const other = screen.getByTestId('preset-PipTopLeft')
    expect(other.className).toContain('border-gray-700')
  })

  it('calls selectPreset when a preset is clicked', () => {
    useComposeStore.setState({ presets: ALL_PRESETS })

    render(<LayoutSelector />)

    fireEvent.click(screen.getByTestId('preset-Grid2x2'))

    expect(useComposeStore.getState().selectedPreset).toBe('Grid2x2')
  })

  it('updates selection when a different preset is clicked', () => {
    useComposeStore.setState({ presets: ALL_PRESETS })

    render(<LayoutSelector />)

    fireEvent.click(screen.getByTestId('preset-PipTopLeft'))
    expect(useComposeStore.getState().selectedPreset).toBe('PipTopLeft')

    fireEvent.click(screen.getByTestId('preset-TopBottom'))
    expect(useComposeStore.getState().selectedPreset).toBe('TopBottom')
  })
})
