import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import {
  getRegisteredShortcuts,
  useKeyboardShortcuts,
  type ShortcutBinding,
} from '../../hooks/useKeyboardShortcuts'

const SECTION_ORDER = ['Global', 'Render', 'Navigation', 'Other'] as const

function groupBySection(
  shortcuts: ShortcutBinding[],
): Map<string, ShortcutBinding[]> {
  const groups = new Map<string, ShortcutBinding[]>()
  for (const shortcut of shortcuts) {
    const section = shortcut.section ?? 'Other'
    const bucket = groups.get(section) ?? []
    bucket.push(shortcut)
    groups.set(section, bucket)
  }
  return groups
}

function sortedSections(groups: Map<string, ShortcutBinding[]>): string[] {
  return Array.from(groups.keys()).sort((a, b) => {
    const ai = SECTION_ORDER.indexOf(a as (typeof SECTION_ORDER)[number])
    const bi = SECTION_ORDER.indexOf(b as (typeof SECTION_ORDER)[number])
    if (ai === -1 && bi === -1) return a.localeCompare(b)
    if (ai === -1) return 1
    if (bi === -1) return -1
    return ai - bi
  })
}

interface OverlayContentProps {
  shortcuts: ShortcutBinding[]
  onClose: () => void
}

function OverlayContent({ shortcuts, onClose }: OverlayContentProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const groups = useMemo(() => groupBySection(shortcuts), [shortcuts])
  const sections = useMemo(() => sortedSections(groups), [groups])

  useFocusTrap(containerRef)

  useEffect(() => {
    const handler = (event: KeyboardEvent): void => {
      if (event.key !== 'Escape') return
      event.preventDefault()
      event.stopPropagation()
      onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      data-testid="keyboard-shortcut-overlay-backdrop"
    >
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="keyboard-shortcut-overlay-title"
        data-testid="keyboard-shortcut-overlay"
        className="max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-lg border border-gray-700 bg-gray-900 p-6 shadow-xl"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2
            id="keyboard-shortcut-overlay-title"
            className="text-xl font-semibold text-gray-100"
          >
            Keyboard Shortcuts
          </h2>
          <button
            type="button"
            onClick={onClose}
            data-testid="btn-close-shortcut-overlay"
            aria-label="Close keyboard shortcuts"
            className="rounded px-2 py-1 text-sm text-gray-400 hover:bg-gray-800 hover:text-gray-100"
          >
            Close
          </button>
        </div>
        {sections.length === 0 ? (
          <p className="text-sm text-gray-400" data-testid="shortcut-overlay-empty">
            No keyboard shortcuts registered.
          </p>
        ) : (
          <div className="space-y-4">
            {sections.map((section) => {
              const items = groups.get(section) ?? []
              return (
                <section
                  key={section}
                  data-testid={`shortcut-section-${section}`}
                >
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
                    {section}
                  </h3>
                  <ul className="divide-y divide-gray-800 rounded border border-gray-800">
                    {items.map((item) => (
                      <li
                        key={item.combo}
                        className="flex items-center justify-between gap-4 px-3 py-2 text-sm text-gray-200"
                        data-testid={`shortcut-${item.combo}`}
                      >
                        <span>{item.description ?? item.action}</span>
                        <kbd className="rounded border border-gray-700 bg-gray-800 px-2 py-0.5 font-mono text-xs">
                          {item.combo}
                        </kbd>
                      </li>
                    ))}
                  </ul>
                </section>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Modal overlay that lists every registered keyboard shortcut, grouped by
 * section. Triggered by the `?` key (BL-294).
 *
 * - Self-registers `?` via `useKeyboardShortcuts` (skipped when a form input
 *   has focus, so typing `?` into a text field still inserts the character).
 * - Reads bindings dynamically from the shortcut registry — new shortcuts
 *   added by other features appear automatically.
 * - Traps focus inside the dialog while open and restores focus to the
 *   previously focused element when closed.
 * - Escape closes the overlay.
 */
export function KeyboardShortcutOverlay(): React.JSX.Element | null {
  const [isOpen, setIsOpen] = useState(false)
  const previouslyFocusedRef = useRef<HTMLElement | null>(null)

  const toggleOverlay = useCallback(() => {
    setIsOpen((prev) => {
      if (!prev) {
        previouslyFocusedRef.current = document.activeElement as HTMLElement | null
      }
      return !prev
    })
  }, [])

  const closeOverlay = useCallback(() => {
    setIsOpen(false)
  }, [])

  const bindings = useMemo<ShortcutBinding[]>(
    () => [
      {
        combo: '?',
        action: 'shortcuts.overlay.toggle',
        description: 'Show keyboard shortcuts',
        section: 'Global',
        handler: toggleOverlay,
      },
    ],
    [toggleOverlay],
  )

  useKeyboardShortcuts(bindings)

  useEffect(() => {
    if (isOpen) return
    const previous = previouslyFocusedRef.current
    if (previous && typeof previous.focus === 'function') {
      previous.focus()
    }
    previouslyFocusedRef.current = null
  }, [isOpen])

  // Capture the registry snapshot once per open transition so the rendered
  // list reflects the bindings present when the user opened the overlay.
  const shortcuts = useMemo(
    () => (isOpen ? getRegisteredShortcuts() : []),
    [isOpen],
  )

  if (!isOpen) return null
  return <OverlayContent shortcuts={shortcuts} onClose={closeOverlay} />
}

export default KeyboardShortcutOverlay
