import { render, screen } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import LayoutPreview from '../LayoutPreview'
import { useComposeStore } from '../../stores/composeStore'
import { PRESET_POSITIONS } from '../../data/presetPositions'

beforeEach(() => {
  useComposeStore.getState().reset()
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
    for (const presetName of Object.keys(PRESET_POSITIONS)) {
      useComposeStore.getState().selectPreset(presetName)

      const { unmount } = render(<LayoutPreview />)
      const positions = PRESET_POSITIONS[presetName]

      for (let i = 0; i < positions.length; i++) {
        const rect = screen.getByTestId(`preview-rect-${i}`)
        expect(rect.style.left).toBe(`${positions[i].x * 100}%`)
        expect(rect.style.top).toBe(`${positions[i].y * 100}%`)
        expect(rect.style.width).toBe(`${positions[i].width * 100}%`)
        expect(rect.style.height).toBe(`${positions[i].height * 100}%`)
      }

      unmount()
    }
  })
})
