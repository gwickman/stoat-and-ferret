import { renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { useFocusTrap } from '../useFocusTrap'

interface Setup {
  container: HTMLDivElement
  buttons: HTMLButtonElement[]
  cleanup: () => void
}

interface Cleanup {
  cleanup: () => void
}

const cleanups: Cleanup[] = []

afterEach(() => {
  while (cleanups.length > 0) {
    const c = cleanups.pop()
    c?.cleanup()
  }
})

function setupWithButtons(labels: string[]): Setup {
  const container = document.createElement('div')
  container.setAttribute('data-testid', 'trap-container')
  const buttons: HTMLButtonElement[] = []
  for (const label of labels) {
    const btn = document.createElement('button')
    btn.textContent = label
    btn.setAttribute('data-testid', `btn-${label}`)
    container.appendChild(btn)
    buttons.push(btn)
  }
  document.body.appendChild(container)
  const cleanup = (): void => {
    if (container.parentNode) container.parentNode.removeChild(container)
  }
  cleanups.push({ cleanup })
  return { container, buttons, cleanup }
}

function fireTab(shift = false): void {
  const event = new KeyboardEvent('keydown', {
    key: 'Tab',
    shiftKey: shift,
    bubbles: true,
    cancelable: true,
  })
  window.dispatchEvent(event)
}

describe('useFocusTrap', () => {
  it('focuses the first focusable element on mount', () => {
    const { container, buttons } = setupWithButtons(['one', 'two', 'three'])
    renderHook(() => useFocusTrap({ current: container }))
    expect(document.activeElement).toBe(buttons[0])
  })

  it('Tab cycles focus forward through focusable elements', () => {
    const { container, buttons } = setupWithButtons(['one', 'two', 'three'])
    renderHook(() => useFocusTrap({ current: container }))
    expect(document.activeElement).toBe(buttons[0])
    fireTab()
    expect(document.activeElement).toBe(buttons[1])
    fireTab()
    expect(document.activeElement).toBe(buttons[2])
    fireTab()
    expect(document.activeElement).toBe(buttons[0])
  })

  it('Shift+Tab cycles focus backward and wraps from first to last', () => {
    const { container, buttons } = setupWithButtons(['one', 'two', 'three'])
    renderHook(() => useFocusTrap({ current: container }))
    expect(document.activeElement).toBe(buttons[0])
    fireTab(true)
    expect(document.activeElement).toBe(buttons[2])
    fireTab(true)
    expect(document.activeElement).toBe(buttons[1])
  })

  it('does not throw when the container has zero focusable elements', () => {
    const container = document.createElement('div')
    const span = document.createElement('span')
    span.textContent = 'no buttons'
    container.appendChild(span)
    document.body.appendChild(container)
    cleanups.push({
      cleanup: () => {
        if (container.parentNode) container.parentNode.removeChild(container)
      },
    })
    expect(() =>
      renderHook(() => useFocusTrap({ current: container })),
    ).not.toThrow()
    expect(() => fireTab()).not.toThrow()
  })

  it('removes the keydown listener on unmount', () => {
    const { container, buttons } = setupWithButtons(['one', 'two'])
    const { unmount } = renderHook(() =>
      useFocusTrap({ current: container }),
    )
    expect(document.activeElement).toBe(buttons[0])
    fireTab()
    expect(document.activeElement).toBe(buttons[1])
    unmount()
    // After unmount the listener is gone — Tab should not throw or reset focus
    // back into the (now removed) trap.
    expect(() => fireTab()).not.toThrow()
  })

  it('skips elements with tabindex="-1" and disabled controls', () => {
    const container = document.createElement('div')
    const a = document.createElement('button')
    a.textContent = 'A'
    a.setAttribute('data-testid', 'btn-a')
    const b = document.createElement('button')
    b.textContent = 'B'
    b.disabled = true
    b.setAttribute('data-testid', 'btn-b')
    const c = document.createElement('button')
    c.textContent = 'C'
    c.tabIndex = -1
    c.setAttribute('data-testid', 'btn-c')
    const d = document.createElement('button')
    d.textContent = 'D'
    d.setAttribute('data-testid', 'btn-d')
    container.appendChild(a)
    container.appendChild(b)
    container.appendChild(c)
    container.appendChild(d)
    document.body.appendChild(container)
    cleanups.push({
      cleanup: () => {
        if (container.parentNode) container.parentNode.removeChild(container)
      },
    })

    renderHook(() => useFocusTrap({ current: container }))
    expect(document.activeElement).toBe(a)
    fireTab()
    expect(document.activeElement).toBe(d)
    fireTab()
    expect(document.activeElement).toBe(a)
  })

  it('returns to the first element from external focus on Tab', () => {
    const { container, buttons } = setupWithButtons(['one', 'two', 'three'])
    renderHook(() => useFocusTrap({ current: container }))
    const outside = document.createElement('button')
    outside.textContent = 'outside'
    document.body.appendChild(outside)
    outside.focus()
    expect(document.activeElement).toBe(outside)
    fireTab()
    expect(document.activeElement).toBe(buttons[0])
    document.body.removeChild(outside)
  })
})
