import { renderHook, act } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { useAnnounce } from '../useAnnounce'

describe('useAnnounce', () => {
  let region: HTMLDivElement
  let assertiveRegion: HTMLDivElement

  beforeEach(() => {
    region = document.createElement('div')
    region.id = 'announcements'
    document.body.appendChild(region)

    assertiveRegion = document.createElement('div')
    assertiveRegion.id = 'announcements-assertive'
    document.body.appendChild(assertiveRegion)
  })

  afterEach(() => {
    if (region.parentNode) {
      region.parentNode.removeChild(region)
    }
    if (assertiveRegion.parentNode) {
      assertiveRegion.parentNode.removeChild(assertiveRegion)
    }
  })

  it('announce(message) updates aria-live region text', () => {
    const { result } = renderHook(() => useAnnounce())
    act(() => {
      result.current.announce('Render complete')
    })
    expect(region.textContent).toBe('Render complete')
  })

  it('announce("") clears region text', () => {
    const { result } = renderHook(() => useAnnounce())
    act(() => {
      result.current.announce('Something happened')
    })
    expect(region.textContent).toBe('Something happened')
    act(() => {
      result.current.announce('')
    })
    expect(region.textContent).toBe('')
  })

  it('multiple calls overwrite previous text', () => {
    const { result } = renderHook(() => useAnnounce())
    act(() => {
      result.current.announce('First message')
    })
    act(() => {
      result.current.announce('Second message')
    })
    expect(region.textContent).toBe('Second message')
  })

  it('cleanup on unmount sets ref to null; subsequent announce is a no-op', () => {
    const { result, unmount } = renderHook(() => useAnnounce())
    act(() => {
      result.current.announce('Before unmount')
    })
    expect(region.textContent).toBe('Before unmount')
    unmount()
    // After unmount regionRef is null; calling announce should not throw
    expect(() => result.current.announce('After unmount')).not.toThrow()
    // Region text remains from before unmount since hook ref is cleared
    expect(region.textContent).toBe('Before unmount')
  })

  it('announce(message, "polite") updates the polite aria-live region', () => {
    const { result } = renderHook(() => useAnnounce())
    act(() => {
      result.current.announce('Polite message', 'polite')
    })
    expect(region.textContent).toBe('Polite message')
    expect(assertiveRegion.textContent).toBe('')
  })

  it('announce(message, "assertive") updates the assertive aria-live region', () => {
    const { result } = renderHook(() => useAnnounce())
    act(() => {
      result.current.announce('Error: operation failed', 'assertive')
    })
    expect(assertiveRegion.textContent).toBe('Error: operation failed')
    expect(region.textContent).toBe('')
  })

  it('assertive and polite regions are updated independently', () => {
    const { result } = renderHook(() => useAnnounce())
    act(() => {
      result.current.announce('Progress: 50%', 'polite')
    })
    act(() => {
      result.current.announce('Error: failed', 'assertive')
    })
    expect(region.textContent).toBe('Progress: 50%')
    expect(assertiveRegion.textContent).toBe('Error: failed')
  })

  it('announce without priority defaults to polite region', () => {
    const { result } = renderHook(() => useAnnounce())
    act(() => {
      result.current.announce('Default priority message')
    })
    expect(region.textContent).toBe('Default priority message')
    expect(assertiveRegion.textContent).toBe('')
  })
})
