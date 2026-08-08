import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ProgressBar from '../ProgressBar'

describe('ProgressBar keyboard navigation', () => {
  it.each([
    { key: 'ArrowRight', currentTime: 10, duration: 60, expectedSeek: 15 },
    { key: 'ArrowLeft',  currentTime: 10, duration: 60, expectedSeek: 5  },
    { key: 'ArrowLeft',  currentTime: 3,  duration: 60, expectedSeek: 0  },
  ])('keyboard seek: $key from t=$currentTime expects onSeek($expectedSeek)', ({ key, currentTime, duration, expectedSeek }) => {
    const onSeek = vi.fn()
    render(<ProgressBar currentTime={currentTime} duration={duration} onSeek={onSeek} />)
    const track = screen.getByTestId('progress-bar-track')
    fireEvent.keyDown(track, { key })
    expect(onSeek).toHaveBeenCalledWith(expectedSeek)
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
