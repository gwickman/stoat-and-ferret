import { renderHook, act } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { useAnnounce } from '../useAnnounce'

describe('useAnnounce', () => {
  let region: HTMLDivElement

  beforeEach(() => {
    region = document.createElement('div')
    region.id = 'announcements'
    document.body.appendChild(region)
  })

  afterEach(() => {
    if (region.parentNode) {
      region.parentNode.removeChild(region)
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
})
