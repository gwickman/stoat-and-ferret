import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import LayerStack from '../LayerStack'
import { useComposeStore } from '../../stores/composeStore'

beforeEach(() => {
  useComposeStore.getState().reset()
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
