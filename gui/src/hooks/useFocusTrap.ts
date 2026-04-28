import { useEffect, type RefObject } from 'react'

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

function focusableWithin(container: HTMLElement): HTMLElement[] {
  // The base selector matches button/input/select/textarea regardless of an
  // explicit tabindex="-1" override, so apply a second filter to honour
  // tabindex="-1" on those elements.
  return Array.from(
    container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
  ).filter((el) => el.getAttribute('tabindex') !== '-1')
}

/**
 * Trap keyboard focus inside the container referenced by `containerRef` while
 * the hook is mounted.
 *
 * Behaviour:
 * - Tab moves focus to the next focusable descendant (wraps from last to first).
 * - Shift+Tab moves focus to the previous focusable descendant (wraps from
 *   first to last).
 * - The first focusable descendant is focused on mount.
 * - Containers with zero focusable descendants are no-ops on Tab; no error is
 *   raised. Restoring focus to the previously focused element is the caller's
 *   responsibility — the hook only manages focus while mounted.
 *
 * The keydown listener is attached to `window` and removed on unmount.
 */
export function useFocusTrap(containerRef: RefObject<HTMLElement | null>): void {
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    focusableWithin(container)[0]?.focus()

    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key !== 'Tab') return
      const current = containerRef.current
      if (!current) return
      const elements = focusableWithin(current)
      event.preventDefault()
      if (elements.length === 0) return
      const active = document.activeElement as HTMLElement | null
      const currentIndex = active ? elements.indexOf(active) : -1
      let nextIndex: number
      if (currentIndex === -1) {
        nextIndex = event.shiftKey ? elements.length - 1 : 0
      } else {
        nextIndex = event.shiftKey
          ? (currentIndex - 1 + elements.length) % elements.length
          : (currentIndex + 1) % elements.length
      }
      elements[nextIndex]?.focus()
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [containerRef])
}
