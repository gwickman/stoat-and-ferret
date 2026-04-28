import { act, render, screen } from '@testing-library/react'
import { useMemo } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  _resetShortcutRegistryForTests,
  useKeyboardShortcuts,
  type ShortcutBinding,
} from '../../../hooks/useKeyboardShortcuts'
import { KeyboardShortcutOverlay } from '../KeyboardShortcutOverlay'

function fireKey(
  key: string,
  modifiers: { ctrl?: boolean; shift?: boolean; alt?: boolean; meta?: boolean } = {},
  target?: EventTarget | null,
): void {
  const event = new KeyboardEvent('keydown', {
    key,
    ctrlKey: !!modifiers.ctrl,
    shiftKey: !!modifiers.shift,
    altKey: !!modifiers.alt,
    metaKey: !!modifiers.meta,
    bubbles: true,
    cancelable: true,
  })
  if (target !== undefined) {
    Object.defineProperty(event, 'target', { value: target })
  }
  window.dispatchEvent(event)
}

interface HostBindings {
  bindings: ShortcutBinding[]
}

function HostWithExtraBindings({ bindings }: HostBindings) {
  const stable = useMemo(() => bindings, [bindings])
  useKeyboardShortcuts(stable)
  return <KeyboardShortcutOverlay />
}

beforeEach(() => {
  _resetShortcutRegistryForTests()
})

afterEach(() => {
  _resetShortcutRegistryForTests()
})

describe('KeyboardShortcutOverlay', () => {
  it('does not render its dialog when closed', () => {
    render(<KeyboardShortcutOverlay />)
    expect(screen.queryByTestId('keyboard-shortcut-overlay')).toBeNull()
  })

  it('opens overlay when ? key is pressed', () => {
    render(<KeyboardShortcutOverlay />)
    expect(screen.queryByTestId('keyboard-shortcut-overlay')).toBeNull()
    act(() => {
      fireKey('?', { shift: true })
    })
    expect(screen.getByTestId('keyboard-shortcut-overlay')).toBeInTheDocument()
  })

  it('toggles closed when ? is pressed while open', () => {
    render(<KeyboardShortcutOverlay />)
    act(() => {
      fireKey('?', { shift: true })
    })
    expect(screen.getByTestId('keyboard-shortcut-overlay')).toBeInTheDocument()
    act(() => {
      fireKey('?', { shift: true })
    })
    expect(screen.queryByTestId('keyboard-shortcut-overlay')).toBeNull()
  })

  it('does not open when ? is pressed inside a form input', () => {
    render(<KeyboardShortcutOverlay />)
    const input = document.createElement('input')
    document.body.appendChild(input)
    input.focus()
    act(() => {
      fireKey('?', { shift: true }, input)
    })
    expect(screen.queryByTestId('keyboard-shortcut-overlay')).toBeNull()
    document.body.removeChild(input)
  })

  it('shows shortcuts registered by other features (Ctrl+1, Ctrl+,) grouped by section', () => {
    const presetEdit = vi.fn()
    const openSettings = vi.fn()
    const bindings: ShortcutBinding[] = [
      {
        combo: 'Ctrl+1',
        action: 'workspace.preset.edit',
        description: 'Switch to Edit preset',
        section: 'Global',
        handler: presetEdit,
      },
      {
        combo: 'Ctrl+,',
        action: 'settings.open',
        description: 'Open settings',
        section: 'Global',
        handler: openSettings,
      },
    ]
    render(<HostWithExtraBindings bindings={bindings} />)

    act(() => {
      fireKey('?', { shift: true })
    })

    expect(screen.getByTestId('keyboard-shortcut-overlay')).toBeInTheDocument()
    expect(screen.getByTestId('shortcut-section-Global')).toBeInTheDocument()
    expect(screen.getByText('Switch to Edit preset')).toBeInTheDocument()
    expect(screen.getByText('Open settings')).toBeInTheDocument()
    // The ? toggle binding registered by the overlay also appears.
    expect(screen.getByText('Show keyboard shortcuts')).toBeInTheDocument()
  })

  it('groups bindings under "Other" when section is omitted', () => {
    const bindings: ShortcutBinding[] = [
      {
        combo: 'Ctrl+B',
        action: 'render.batch.toggle',
        description: 'Toggle batch panel',
        section: 'Render',
        handler: vi.fn(),
      },
      {
        combo: 'Ctrl+L',
        action: 'misc.thing',
        description: 'Misc',
        handler: vi.fn(),
      },
    ]
    render(<HostWithExtraBindings bindings={bindings} />)
    act(() => {
      fireKey('?', { shift: true })
    })
    expect(screen.getByTestId('shortcut-section-Render')).toBeInTheDocument()
    expect(screen.getByTestId('shortcut-section-Other')).toBeInTheDocument()
  })

  it('Escape closes the overlay', () => {
    render(<KeyboardShortcutOverlay />)
    act(() => {
      fireKey('?', { shift: true })
    })
    expect(screen.getByTestId('keyboard-shortcut-overlay')).toBeInTheDocument()
    act(() => {
      fireKey('Escape')
    })
    expect(screen.queryByTestId('keyboard-shortcut-overlay')).toBeNull()
  })

  it('restores focus to the previously focused element after closing', () => {
    render(<KeyboardShortcutOverlay />)
    const trigger = document.createElement('button')
    trigger.textContent = 'Trigger'
    document.body.appendChild(trigger)
    trigger.focus()
    expect(document.activeElement).toBe(trigger)

    act(() => {
      fireKey('?', { shift: true })
    })
    expect(screen.getByTestId('keyboard-shortcut-overlay')).toBeInTheDocument()
    expect(document.activeElement).not.toBe(trigger)

    act(() => {
      fireKey('Escape')
    })
    expect(document.activeElement).toBe(trigger)
    document.body.removeChild(trigger)
  })

  it('clicking the close button closes the overlay', () => {
    render(<KeyboardShortcutOverlay />)
    act(() => {
      fireKey('?', { shift: true })
    })
    const closeBtn = screen.getByTestId('btn-close-shortcut-overlay')
    act(() => {
      closeBtn.click()
    })
    expect(screen.queryByTestId('keyboard-shortcut-overlay')).toBeNull()
  })

  it('Tab keeps focus inside overlay (focus trap)', () => {
    const bindings: ShortcutBinding[] = [
      {
        combo: 'Ctrl+1',
        action: 'workspace.preset.edit',
        description: 'Switch to Edit preset',
        section: 'Global',
        handler: vi.fn(),
      },
    ]
    render(<HostWithExtraBindings bindings={bindings} />)
    act(() => {
      fireKey('?', { shift: true })
    })
    const overlay = screen.getByTestId('keyboard-shortcut-overlay')
    expect(overlay).toBeInTheDocument()
    // Focus should be on the close button (the only focusable inside the
    // overlay). Tab should keep focus inside the overlay.
    const closeBtn = screen.getByTestId('btn-close-shortcut-overlay')
    expect(document.activeElement).toBe(closeBtn)
    act(() => {
      fireKey('Tab')
    })
    // With only one focusable, Tab cycles back to the same element.
    expect(overlay.contains(document.activeElement)).toBe(true)
  })
})
