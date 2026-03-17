import { render, screen } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import LayoutPreview from '../LayoutPreview'
import { useComposeStore } from '../../stores/composeStore'
import type { LayoutPreset } from '../../types/timeline'

/** Test preset data matching Rust LayoutPreset definitions. */
const TEST_PRESETS: LayoutPreset[] = [
  {
    name: 'PipTopLeft',
    description: 'PIP top-left',
    ai_hint: '',
    min_inputs: 2,
    max_inputs: 2,
    positions: [
      { x: 0.0, y: 0.0, width: 1.0, height: 1.0, z_index: 0 },
      { x: 0.02, y: 0.02, width: 0.25, height: 0.25, z_index: 1 },
    ],
  },
  {
    name: 'PipTopRight',
    description: 'PIP top-right',
    ai_hint: '',
    min_inputs: 2,
    max_inputs: 2,
    positions: [
      { x: 0.0, y: 0.0, width: 1.0, height: 1.0, z_index: 0 },
      { x: 0.73, y: 0.02, width: 0.25, height: 0.25, z_index: 1 },
    ],
  },
  {
    name: 'PipBottomLeft',
    description: 'PIP bottom-left',
    ai_hint: '',
    min_inputs: 2,
    max_inputs: 2,
    positions: [
      { x: 0.0, y: 0.0, width: 1.0, height: 1.0, z_index: 0 },
      { x: 0.02, y: 0.73, width: 0.25, height: 0.25, z_index: 1 },
    ],
  },
  {
    name: 'PipBottomRight',
    description: 'PIP bottom-right',
    ai_hint: '',
    min_inputs: 2,
    max_inputs: 2,
    positions: [
      { x: 0.0, y: 0.0, width: 1.0, height: 1.0, z_index: 0 },
      { x: 0.73, y: 0.73, width: 0.25, height: 0.25, z_index: 1 },
    ],
  },
  {
    name: 'SideBySide',
    description: 'Side by side',
    ai_hint: '',
    min_inputs: 2,
    max_inputs: 2,
    positions: [
      { x: 0.0, y: 0.0, width: 0.5, height: 1.0, z_index: 0 },
      { x: 0.5, y: 0.0, width: 0.5, height: 1.0, z_index: 0 },
    ],
  },
  {
    name: 'TopBottom',
    description: 'Top bottom',
    ai_hint: '',
    min_inputs: 2,
    max_inputs: 2,
    positions: [
      { x: 0.0, y: 0.0, width: 1.0, height: 0.5, z_index: 0 },
      { x: 0.0, y: 0.5, width: 1.0, height: 0.5, z_index: 0 },
    ],
  },
  {
    name: 'Grid2x2',
    description: '2x2 grid',
    ai_hint: '',
    min_inputs: 4,
    max_inputs: 4,
    positions: [
      { x: 0.0, y: 0.0, width: 0.5, height: 0.5, z_index: 0 },
      { x: 0.5, y: 0.0, width: 0.5, height: 0.5, z_index: 0 },
      { x: 0.0, y: 0.5, width: 0.5, height: 0.5, z_index: 0 },
      { x: 0.5, y: 0.5, width: 0.5, height: 0.5, z_index: 0 },
    ],
  },
]

beforeEach(() => {
  useComposeStore.getState().reset()
  // Populate presets so selectPreset can look up positions from API data
  useComposeStore.setState({ presets: TEST_PRESETS })
})

describe('LayoutPreview', () => {
  it('shows placeholder when no preset is selected', () => {
    render(<LayoutPreview />)

    expect(screen.getByTestId('layout-preview')).toBeDefined()
    expect(screen.getByText('Select a preset to preview')).toBeDefined()
  })

  it('renders rectangles for PipTopLeft preset', () => {
    useComposeStore.getState().selectPreset('PipTopLeft')

    render(<LayoutPreview />)

    const rect0 = screen.getByTestId('preview-rect-0')
    const rect1 = screen.getByTestId('preview-rect-1')

    expect(rect0).toBeDefined()
    expect(rect1).toBeDefined()

    // Verify position matches preset coordinates
    expect(rect0.style.left).toBe('0%')
    expect(rect0.style.top).toBe('0%')
    expect(rect0.style.width).toBe('100%')
    expect(rect0.style.height).toBe('100%')

    expect(rect1.style.left).toBe('2%')
    expect(rect1.style.top).toBe('2%')
    expect(rect1.style.width).toBe('25%')
    expect(rect1.style.height).toBe('25%')
  })

  it('renders rectangles for SideBySide preset', () => {
    useComposeStore.getState().selectPreset('SideBySide')

    render(<LayoutPreview />)

    const rect0 = screen.getByTestId('preview-rect-0')
    const rect1 = screen.getByTestId('preview-rect-1')

    expect(rect0.style.left).toBe('0%')
    expect(rect0.style.width).toBe('50%')
    expect(rect1.style.left).toBe('50%')
    expect(rect1.style.width).toBe('50%')
  })

  it('renders 4 rectangles for Grid2x2 preset', () => {
    useComposeStore.getState().selectPreset('Grid2x2')

    render(<LayoutPreview />)

    for (let i = 0; i < 4; i++) {
      expect(screen.getByTestId(`preview-rect-${i}`)).toBeDefined()
    }
    expect(screen.queryByTestId('preview-rect-4')).toBeNull()
  })

  it('updates rectangles when preset changes', () => {
    useComposeStore.getState().selectPreset('PipTopLeft')

    const { rerender } = render(<LayoutPreview />)

    expect(screen.getByTestId('preview-rect-1').style.left).toBe('2%')

    useComposeStore.getState().selectPreset('PipTopRight')
    rerender(<LayoutPreview />)

    expect(screen.getByTestId('preview-rect-1').style.left).toBe('73%')
  })

  it('renders correct z-index on rectangles', () => {
    useComposeStore.getState().selectPreset('PipBottomRight')

    render(<LayoutPreview />)

    const rect0 = screen.getByTestId('preview-rect-0')
    const rect1 = screen.getByTestId('preview-rect-1')

    expect(rect0.style.zIndex).toBe('0')
    expect(rect1.style.zIndex).toBe('1')
  })

  it('renders rectangles for all 7 presets', () => {
    for (const preset of TEST_PRESETS) {
      useComposeStore.getState().selectPreset(preset.name)

      const { unmount } = render(<LayoutPreview />)

      for (let i = 0; i < preset.positions.length; i++) {
        const rect = screen.getByTestId(`preview-rect-${i}`)
        expect(rect.style.left).toBe(`${preset.positions[i].x * 100}%`)
        expect(rect.style.top).toBe(`${preset.positions[i].y * 100}%`)
        expect(rect.style.width).toBe(`${preset.positions[i].width * 100}%`)
        expect(rect.style.height).toBe(`${preset.positions[i].height * 100}%`)
      }

      unmount()
    }
  })
})
