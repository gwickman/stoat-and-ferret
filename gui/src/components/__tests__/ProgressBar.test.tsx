import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ProgressBar from '../ProgressBar'

describe('ProgressBar keyboard navigation', () => {
  it('ArrowRight seeks forward 5s from currentTime=10', () => {
    const onSeek = vi.fn()
    render(<ProgressBar currentTime={10} duration={60} onSeek={onSeek} />)
    const track = screen.getByTestId('progress-bar-track')
    fireEvent.keyDown(track, { key: 'ArrowRight' })
    expect(onSeek).toHaveBeenCalledWith(15)
  })

  it('ArrowLeft seeks backward 5s from currentTime=10', () => {
    const onSeek = vi.fn()
    render(<ProgressBar currentTime={10} duration={60} onSeek={onSeek} />)
    const track = screen.getByTestId('progress-bar-track')
    fireEvent.keyDown(track, { key: 'ArrowLeft' })
    expect(onSeek).toHaveBeenCalledWith(5)
  })

  it('ArrowLeft clamps to 0 when currentTime=3', () => {
    const onSeek = vi.fn()
    render(<ProgressBar currentTime={3} duration={60} onSeek={onSeek} />)
    const track = screen.getByTestId('progress-bar-track')
    fireEvent.keyDown(track, { key: 'ArrowLeft' })
    expect(onSeek).toHaveBeenCalledWith(0)
  })

  it('stopPropagation prevents ArrowRight from reaching parent onKeyDown handler', () => {
    const onSeek = vi.fn()
    const parentKeyDown = vi.fn()
    render(
      // role="toolbar" mirrors the PlayerControls wrapper; onKeyDown verifies no bubble
      <div role="toolbar" aria-label="player" onKeyDown={parentKeyDown}>
        <ProgressBar currentTime={10} duration={60} onSeek={onSeek} />
      </div>,
    )
    const track = screen.getByTestId('progress-bar-track')
    fireEvent.keyDown(track, { key: 'ArrowRight' })
    expect(onSeek).toHaveBeenCalledWith(15)
    expect(parentKeyDown).not.toHaveBeenCalled()
  })
})
