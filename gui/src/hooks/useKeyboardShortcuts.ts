import { useEffect } from 'react'

/** Tags for which keyboard shortcuts should be skipped (form input guard). */
const SKIP_TAGS: ReadonlySet<string> = new Set(['INPUT', 'TEXTAREA', 'SELECT'])

export interface ShortcutBinding {
  /** Combo string in the form "Ctrl+1", "Ctrl+Shift+P". */
  combo: string
  /** Human-readable action name (used in console.warn on duplicate). */
  action: string
  /** Handler invoked when the combo fires. */
  handler: () => void
  /**
   * Optional human-readable description shown in the keyboard shortcut
   * overlay. Falls back to `action` when omitted.
   */
  description?: string
  /**
   * Optional section name used to group bindings in the overlay (e.g.,
   * "Global", "Render", "Navigation"). Bindings without a section are
   * grouped under "Other".
   */
  section?: string
}

interface ParsedCombo {
  ctrlOrMeta: boolean
  shift: boolean
  alt: boolean
  /** The non-modifier key, lower-cased. */
  key: string
}

interface RegistryEntry {
  combo: ParsedCombo
  binding: ShortcutBinding
}

/**
 * Module-level registry of registered shortcuts. Each registered combo string
 * maps to the first-registered action; subsequent registrations of the same
 * combo emit `console.warn` and are ignored.
 */
const registry = new Map<string, RegistryEntry>()

let listenerAttached = false

function parseCombo(combo: string): ParsedCombo {
  const parts = combo.split('+').map((p) => p.trim())
  const result: ParsedCombo = { ctrlOrMeta: false, shift: false, alt: false, key: '' }
  for (const part of parts) {
    const lower = part.toLowerCase()
    if (lower === 'ctrl' || lower === 'control' || lower === 'cmd' || lower === 'meta') {
      result.ctrlOrMeta = true
    } else if (lower === 'shift') {
      result.shift = true
    } else if (lower === 'alt' || lower === 'option') {
      result.alt = true
    } else {
      result.key = lower
    }
  }
  return result
}

function eventMatches(combo: ParsedCombo, event: KeyboardEvent): boolean {
  if (combo.ctrlOrMeta && !(event.ctrlKey || event.metaKey)) return false
  if (!combo.ctrlOrMeta && (event.ctrlKey || event.metaKey)) return false
  // A combo that explicitly names Shift requires Shift; otherwise we accept
  // both shifted and non-shifted events. Strict equality on Shift would
  // reject combos whose key is itself a shifted character (e.g. "?" produced
  // by Shift+/), forcing callers to write "Shift+?".
  if (combo.shift && !event.shiftKey) return false
  if (combo.alt !== event.altKey) return false
  return event.key.toLowerCase() === combo.key
}

function isFormInputTarget(target: EventTarget | null): boolean {
  if (!target) return false
  const tagName = (target as { tagName?: unknown }).tagName
  return typeof tagName === 'string' && SKIP_TAGS.has(tagName)
}

function handleKeyDown(event: KeyboardEvent): void {
  if (isFormInputTarget(event.target)) return
  for (const entry of registry.values()) {
    if (eventMatches(entry.combo, event)) {
      event.preventDefault()
      entry.binding.handler()
      return
    }
  }
}

function attachListenerOnce(): void {
  if (listenerAttached) return
  if (typeof window === 'undefined') return
  window.addEventListener('keydown', handleKeyDown)
  listenerAttached = true
}

/**
 * Register a set of keyboard shortcut bindings while the calling component is
 * mounted. Bindings are added to a module-level registry on mount and removed
 * on unmount. Duplicate combo registrations are rejected with a `console.warn`
 * (first-registered-wins).
 *
 * **Form input guard**: combos do not fire when an INPUT, TEXTAREA, or SELECT
 * element is the event target — matching the pattern from `useTheaterShortcuts`.
 *
 * **Caller contract**: pass a stable bindings array (module-level constant or
 * `useMemo`) — re-rendering with a new array reference re-registers the
 * combos, which can lose the first-registered guarantee.
 */
export function useKeyboardShortcuts(bindings: ShortcutBinding[]): void {
  useEffect(() => {
    attachListenerOnce()
    const added: string[] = []
    for (const binding of bindings) {
      const existing = registry.get(binding.combo)
      if (existing) {
        console.warn(
          `useKeyboardShortcuts: combo "${binding.combo}" already registered for action ` +
            `"${existing.binding.action}"; ignoring registration for "${binding.action}"`,
        )
        continue
      }
      registry.set(binding.combo, { combo: parseCombo(binding.combo), binding })
      added.push(binding.combo)
    }
    return () => {
      for (const combo of added) registry.delete(combo)
    }
  }, [bindings])
}

/**
 * Snapshot of the bindings currently in the module-level registry, in
 * registration order. Used by the keyboard shortcut overlay (BL-294) to
 * render a read-only reference of every registered combo without hardcoding
 * the list. The returned array is a copy — mutating it does not affect the
 * registry.
 */
export function getRegisteredShortcuts(): ShortcutBinding[] {
  return Array.from(registry.values()).map((entry) => entry.binding)
}

/** @internal Test-only helper for resetting module state between cases. */
export function _resetShortcutRegistryForTests(): void {
  registry.clear()
  if (listenerAttached && typeof window !== 'undefined') {
    window.removeEventListener('keydown', handleKeyDown)
    listenerAttached = false
  }
}
