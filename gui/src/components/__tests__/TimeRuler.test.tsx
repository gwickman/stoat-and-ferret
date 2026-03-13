import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import TimeRuler from '../TimeRuler'

describe('TimeRuler', () => {
  it('renders ruler element', () => {
    render(
      <TimeRuler duration={10} zoom={1} scrollOffset={0} canvasWidth={800} />,
    )

    expect(screen.getByTestId('time-ruler')).toBeDefined()
  })

  it('shows time markers at appropriate intervals', () => {
    render(
      <TimeRuler duration={5} zoom={1} scrollOffset={0} canvasWidth={800} />,
    )

    // At zoom 1, 100px/s, interval = 1s. Duration 5s → markers at 0,1,2,3,4,5
    expect(screen.getByTestId('ruler-marker-0')).toBeDefined()
    expect(screen.getByTestId('ruler-marker-1')).toBeDefined()
    expect(screen.getByTestId('ruler-marker-2')).toBeDefined()
    expect(screen.getByTestId('ruler-marker-3')).toBeDefined()
    expect(screen.getByTestId('ruler-marker-4')).toBeDefined()
    expect(screen.getByTestId('ruler-marker-5')).toBeDefined()
  })

  it('adjusts marker density with zoom', () => {
    const { container: zoomedIn } = render(
      <TimeRuler duration={10} zoom={5} scrollOffset={0} canvasWidth={800} />,
    )
    const markersZoomedIn = zoomedIn.querySelectorAll('[data-testid^="ruler-marker-"]')

    const { container: zoomedOut } = render(
      <TimeRuler duration={10} zoom={0.1} scrollOffset={0} canvasWidth={800} />,
    )
    const markersZoomedOut = zoomedOut.querySelectorAll('[data-testid^="ruler-marker-"]')

    // Zoomed out should have fewer markers visible in the same canvas width
    expect(markersZoomedOut.length).toBeLessThan(markersZoomedIn.length)
  })

  it('positions markers using timeToPixel', () => {
    render(
      <TimeRuler duration={3} zoom={1} scrollOffset={0} canvasWidth={400} />,
    )

    // At zoom 1, 100px/s: marker at 1s should be at 100px
    const marker1 = screen.getByTestId('ruler-marker-1')
    expect(marker1.style.left).toBe('100px')

    const marker2 = screen.getByTestId('ruler-marker-2')
    expect(marker2.style.left).toBe('200px')
  })

  it('renders markers only within visible range', () => {
    render(
      <TimeRuler duration={100} zoom={1} scrollOffset={0} canvasWidth={300} />,
    )

    // At 100px/s, canvas 300px: markers at 0, 1, 2, 3 visible
    expect(screen.getByTestId('ruler-marker-0')).toBeDefined()
    expect(screen.getByTestId('ruler-marker-3')).toBeDefined()
    // marker at 4 = 400px > 300+10 → should not render
    expect(screen.queryByTestId('ruler-marker-4')).toBeNull()
  })

  it('accounts for scroll offset', () => {
    render(
      <TimeRuler duration={10} zoom={1} scrollOffset={200} canvasWidth={300} />,
    )

    // Scrolled 200px → time 2s is at pixel 0. Markers at 2,3,4,5 visible
    expect(screen.getByTestId('ruler-marker-2')).toBeDefined()
    expect(screen.getByTestId('ruler-marker-5')).toBeDefined()
  })
})
