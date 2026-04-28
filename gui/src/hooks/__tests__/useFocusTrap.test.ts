import { render } from '@testing-library/react'
import { useRef, createElement, type ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import { useFocusTrap } from '../useFocusTrap'

interface HarnessProps {
  children: ReactNode
}

function Harness({ children }: HarnessProps): ReactNode {
  const ref = useRef<HTMLDivElement>(null)
  useFocusTrap(ref)
  return createElement('div', { ref, 'data-testid': 'trap-container' }, children)
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

function buttons(...labels: string[]): ReactNode[] {
  return labels.map((label) =>
    createElement('button', { key: label, 'data-testid': `btn-${label}` }, label),
  )
}

describe('useFocusTrap', () => {
  it('focuses the first focusable element on mount', () => {
    const { getByTestId } = render(
      createElement(Harness, null, ...buttons('one', 'two', 'three')),
    )
    expect(document.activeElement).toBe(getByTestId('btn-one'))
  })

  it('Tab cycles focus forward through focusable elements', () => {
    const { getByTestId } = render(
      createElement(Harness, null, ...buttons('one', 'two', 'three')),
    )
    expect(document.activeElement).toBe(getByTestId('btn-one'))
    fireTab()
    expect(document.activeElement).toBe(getByTestId('btn-two'))
    fireTab()
    expect(document.activeElement).toBe(getByTestId('btn-three'))
    fireTab()
    expect(document.activeElement).toBe(getByTestId('btn-one'))
  })

  it('Shift+Tab cycles focus backward and wraps from first to last', () => {
    const { getByTestId } = render(
      createElement(Harness, null, ...buttons('one', 'two', 'three')),
    )
    expect(document.activeElement).toBe(getByTestId('btn-one'))
    fireTab(true)
    expect(document.activeElement).toBe(getByTestId('btn-three'))
    fireTab(true)
    expect(document.activeElement).toBe(getByTestId('btn-two'))
  })

  it('does not throw when the container has zero focusable elements', () => {
    expect(() =>
      render(
        createElement(
          Harness,
          null,
          createElement('span', { 'data-testid': 'static' }, 'no buttons'),
        ),
      ),
    ).not.toThrow()
    expect(() => fireTab()).not.toThrow()
  })

  it('removes the keydown listener on unmount', () => {
    const { getByTestId, unmount } = render(
      createElement(Harness, null, ...buttons('one', 'two')),
    )
    expect(document.activeElement).toBe(getByTestId('btn-one'))
    fireTab()
    expect(document.activeElement).toBe(getByTestId('btn-two'))
    unmount()
    // After unmount the listener is gone — Tab should not throw or reset focus
    // back into the (now removed) trap.
    expect(() => fireTab()).not.toThrow()
  })

  it('skips elements with tabindex="-1" and disabled controls', () => {
    const { getByTestId } = render(
      createElement(
        Harness,
        null,
        createElement('button', { key: 'a', 'data-testid': 'btn-a' }, 'A'),
        createElement(
          'button',
          { key: 'b', 'data-testid': 'btn-b', disabled: true },
          'B',
        ),
        createElement(
          'button',
          { key: 'c', 'data-testid': 'btn-c', tabIndex: -1 },
          'C',
        ),
        createElement('button', { key: 'd', 'data-testid': 'btn-d' }, 'D'),
      ),
    )
    expect(document.activeElement).toBe(getByTestId('btn-a'))
    fireTab()
    expect(document.activeElement).toBe(getByTestId('btn-d'))
    fireTab()
    expect(document.activeElement).toBe(getByTestId('btn-a'))
  })

  it('returns to the first element from external focus on Tab', () => {
    const { getByTestId } = render(
      createElement(Harness, null, ...buttons('one', 'two', 'three')),
    )
    // Move focus outside the container
    const outside = document.createElement('button')
    outside.textContent = 'outside'
    document.body.appendChild(outside)
    outside.focus()
    expect(document.activeElement).toBe(outside)
    fireTab()
    expect(document.activeElement).toBe(getByTestId('btn-one'))
    document.body.removeChild(outside)
  })
})
