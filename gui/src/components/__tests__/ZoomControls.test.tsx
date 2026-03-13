import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ZoomControls from '../ZoomControls'

describe('ZoomControls', () => {
  it('renders zoom controls', () => {
    render(
      <ZoomControls zoom={1} onZoomIn={vi.fn()} onZoomOut={vi.fn()} onReset={vi.fn()} />,
    )

    expect(screen.getByTestId('zoom-controls')).toBeDefined()
    expect(screen.getByTestId('zoom-in')).toBeDefined()
    expect(screen.getByTestId('zoom-out')).toBeDefined()
    expect(screen.getByTestId('zoom-reset')).toBeDefined()
  })

  it('displays current zoom percentage', () => {
    render(
      <ZoomControls zoom={1.5} onZoomIn={vi.fn()} onZoomOut={vi.fn()} onReset={vi.fn()} />,
    )

    expect(screen.getByTestId('zoom-reset').textContent).toBe('150%')
  })

  it('calls onZoomIn when + clicked', () => {
    const onZoomIn = vi.fn()
    render(
      <ZoomControls zoom={1} onZoomIn={onZoomIn} onZoomOut={vi.fn()} onReset={vi.fn()} />,
    )

    fireEvent.click(screen.getByTestId('zoom-in'))
    expect(onZoomIn).toHaveBeenCalledOnce()
  })

  it('calls onZoomOut when - clicked', () => {
    const onZoomOut = vi.fn()
    render(
      <ZoomControls zoom={1} onZoomIn={vi.fn()} onZoomOut={onZoomOut} onReset={vi.fn()} />,
    )

    fireEvent.click(screen.getByTestId('zoom-out'))
    expect(onZoomOut).toHaveBeenCalledOnce()
  })

  it('calls onReset when percentage clicked', () => {
    const onReset = vi.fn()
    render(
      <ZoomControls zoom={2} onZoomIn={vi.fn()} onZoomOut={vi.fn()} onReset={onReset} />,
    )

    fireEvent.click(screen.getByTestId('zoom-reset'))
    expect(onReset).toHaveBeenCalledOnce()
  })

  it('disables zoom out at min zoom', () => {
    render(
      <ZoomControls zoom={0.1} onZoomIn={vi.fn()} onZoomOut={vi.fn()} onReset={vi.fn()} minZoom={0.1} />,
    )

    expect(screen.getByTestId('zoom-out')).toHaveProperty('disabled', true)
  })

  it('disables zoom in at max zoom', () => {
    render(
      <ZoomControls zoom={10} onZoomIn={vi.fn()} onZoomOut={vi.fn()} onReset={vi.fn()} maxZoom={10} />,
    )

    expect(screen.getByTestId('zoom-in')).toHaveProperty('disabled', true)
  })
})
