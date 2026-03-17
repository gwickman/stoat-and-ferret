import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import LayerStack from '../LayerStack'
import { useComposeStore } from '../../stores/composeStore'
import type { LayoutPreset } from '../../types/timeline'

const TEST_PRESETS: LayoutPreset[] = [
  {
    name: 'PipTopLeft', description: '', ai_hint: '', min_inputs: 2, max_inputs: 2,
    positions: [
      { x: 0, y: 0, width: 1, height: 1, z_index: 0 },
      { x: 0.02, y: 0.02, width: 0.25, height: 0.25, z_index: 1 },
    ],
  },
  {
    name: 'PipBottomRight', description: '', ai_hint: '', min_inputs: 2, max_inputs: 2,
    positions: [
      { x: 0, y: 0, width: 1, height: 1, z_index: 0 },
      { x: 0.73, y: 0.73, width: 0.25, height: 0.25, z_index: 1 },
    ],
  },
  {
    name: 'SideBySide', description: '', ai_hint: '', min_inputs: 2, max_inputs: 2,
    positions: [
      { x: 0, y: 0, width: 0.5, height: 1, z_index: 0 },
      { x: 0.5, y: 0, width: 0.5, height: 1, z_index: 0 },
    ],
  },
  {
    name: 'Grid2x2', description: '', ai_hint: '', min_inputs: 4, max_inputs: 4,
    positions: [
      { x: 0, y: 0, width: 0.5, height: 0.5, z_index: 0 },
      { x: 0.5, y: 0, width: 0.5, height: 0.5, z_index: 0 },
      { x: 0, y: 0.5, width: 0.5, height: 0.5, z_index: 0 },
      { x: 0.5, y: 0.5, width: 0.5, height: 0.5, z_index: 0 },
    ],
  },
]

beforeEach(() => {
  useComposeStore.getState().reset()
  useComposeStore.setState({ presets: TEST_PRESETS })
})

describe('LayerStack', () => {
  it('shows empty message when no layers', () => {
    render(<LayerStack />)

    expect(screen.getByTestId('layer-stack')).toBeDefined()
    expect(screen.getByText('No layers to display')).toBeDefined()
  })

  it('displays layers sorted by z_index descending', () => {
    useComposeStore.getState().selectPreset('PipTopLeft')

    render(<LayerStack />)

    const list = screen.getByTestId('layer-list')
    const items = list.querySelectorAll('li')

    // Layer 2 (z=1) should appear before Layer 1 (z=0)
    expect(items[0].textContent).toContain('Layer 2')
    expect(items[0].textContent).toContain('z: 1')
    expect(items[1].textContent).toContain('Layer 1')
    expect(items[1].textContent).toContain('z: 0')
  })

  it('shows z-index for each layer', () => {
    useComposeStore.getState().selectPreset('PipBottomRight')

    render(<LayerStack />)

    expect(screen.getByTestId('layer-z-0')).toBeDefined()
    expect(screen.getByTestId('layer-z-0').textContent).toBe('z: 0')
    expect(screen.getByTestId('layer-z-1')).toBeDefined()
    expect(screen.getByTestId('layer-z-1').textContent).toBe('z: 1')
  })

  it('shows 4 layers for Grid2x2 preset', () => {
    useComposeStore.getState().selectPreset('Grid2x2')

    render(<LayerStack />)

    const list = screen.getByTestId('layer-list')
    expect(list.querySelectorAll('li').length).toBe(4)
  })

  it('shows custom position inputs after selecting a preset', () => {
    useComposeStore.getState().selectPreset('SideBySide')

    render(<LayerStack />)

    expect(screen.getByTestId('custom-inputs')).toBeDefined()
    expect(screen.getByTestId('custom-pos-0')).toBeDefined()
    expect(screen.getByTestId('custom-pos-1')).toBeDefined()
  })

  it('custom inputs display coordinate values', () => {
    useComposeStore.getState().selectPreset('SideBySide')

    render(<LayerStack />)

    const xInput = screen.getByTestId('input-0-x') as HTMLInputElement
    const wInput = screen.getByTestId('input-0-width') as HTMLInputElement

    expect(xInput.value).toBe('0')
    expect(wInput.value).toBe('0.5')
  })

  it('custom input change updates store and clears selected preset', () => {
    useComposeStore.getState().selectPreset('SideBySide')

    render(<LayerStack />)

    const xInput = screen.getByTestId('input-0-x') as HTMLInputElement
    fireEvent.change(xInput, { target: { value: '0.1' } })

    expect(useComposeStore.getState().customPositions[0].x).toBe(0.1)
    expect(useComposeStore.getState().selectedPreset).toBeNull()
  })

  it('custom input clamps values outside 0.0-1.0 range', () => {
    useComposeStore.getState().selectPreset('SideBySide')

    render(<LayerStack />)

    const xInput = screen.getByTestId('input-0-x') as HTMLInputElement

    fireEvent.change(xInput, { target: { value: '1.5' } })
    expect(useComposeStore.getState().customPositions[0].x).toBe(1)

    fireEvent.change(xInput, { target: { value: '-0.3' } })
    expect(useComposeStore.getState().customPositions[0].x).toBe(0)
  })

  it('does not show custom inputs when no positions', () => {
    render(<LayerStack />)

    expect(screen.queryByTestId('custom-inputs')).toBeNull()
  })
})
