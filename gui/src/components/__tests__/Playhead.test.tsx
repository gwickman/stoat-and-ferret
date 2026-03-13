import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import Playhead from '../Playhead'

describe('Playhead', () => {
  it('renders at correct pixel position via timeToPixel', () => {
    render(<Playhead position={3} zoom={1} scrollOffset={0} height={96} />)

    const el = screen.getByTestId('playhead')
    // left = 3 * 100 * 1 - 0 = 300
    expect(el.style.left).toBe('300px')
  })

  it('applies zoom to position', () => {
    render(<Playhead position={2} zoom={2} scrollOffset={0} height={96} />)

    const el = screen.getByTestId('playhead')
    // left = 2 * 100 * 2 = 400
    expect(el.style.left).toBe('400px')
  })

  it('accounts for scrollOffset', () => {
    render(<Playhead position={5} zoom={1} scrollOffset={100} height={96} />)

    const el = screen.getByTestId('playhead')
    // left = 5 * 100 - 100 = 400
    expect(el.style.left).toBe('400px')
  })

  it('renders with correct height', () => {
    render(<Playhead position={0} zoom={1} scrollOffset={0} height={144} />)

    const el = screen.getByTestId('playhead')
    expect(el.style.height).toBe('144px')
  })

  it('has aria-label with position', () => {
    render(<Playhead position={2.5} zoom={1} scrollOffset={0} height={96} />)

    const el = screen.getByTestId('playhead')
    expect(el.getAttribute('aria-label')).toBe('Playhead at 2.5s')
  })

  it('renders at position 0 by default', () => {
    render(<Playhead position={0} zoom={1} scrollOffset={0} height={96} />)

    const el = screen.getByTestId('playhead')
    expect(el.style.left).toBe('0px')
  })
})
