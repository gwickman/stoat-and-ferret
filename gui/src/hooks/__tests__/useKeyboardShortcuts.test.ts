import { renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  _resetShortcutRegistryForTests,
  useKeyboardShortcuts,
  type ShortcutBinding,
} from '../useKeyboardShortcuts'

function fireKey(
  key: string,
  modifiers: { ctrl?: boolean; shift?: boolean; alt?: boolean; meta?: boolean } = {},
  target?: EventTarget | null,
) {
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
  return event
}

beforeEach(() => {
  _resetShortcutRegistryForTests()
})

afterEach(() => {
  _resetShortcutRegistryForTests()
})

describe('useKeyboardShortcuts', () => {
  it('invokes handler for matching Ctrl+1 combo', () => {
    const handler = vi.fn()
    const bindings: ShortcutBinding[] = [
      { combo: 'Ctrl+1', action: 'preset.edit', handler },
    ]
    renderHook(() => useKeyboardShortcuts(bindings))
    fireKey('1', { ctrl: true })
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('invokes correct handler for Ctrl+2', () => {
    const editHandler = vi.fn()
    const reviewHandler = vi.fn()
    const bindings: ShortcutBinding[] = [
      { combo: 'Ctrl+1', action: 'preset.edit', handler: editHandler },
      { combo: 'Ctrl+2', action: 'preset.review', handler: reviewHandler },
    ]
    renderHook(() => useKeyboardShortcuts(bindings))
    fireKey('2', { ctrl: true })
    expect(reviewHandler).toHaveBeenCalledTimes(1)
    expect(editHandler).not.toHaveBeenCalled()
  })

  it('invokes correct handler for Ctrl+3', () => {
    const renderHandler = vi.fn()
    const bindings: ShortcutBinding[] = [
      { combo: 'Ctrl+3', action: 'preset.render', handler: renderHandler },
    ]
    renderHook(() => useKeyboardShortcuts(bindings))
    fireKey('3', { ctrl: true })
    expect(renderHandler).toHaveBeenCalledTimes(1)
  })

  it('also fires on Cmd (metaKey) for cross-platform parity', () => {
    const handler = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([{ combo: 'Ctrl+1', action: 'preset.edit', handler }]),
    )
    fireKey('1', { meta: true })
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('ignores plain "1" without Ctrl/Meta', () => {
    const handler = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([{ combo: 'Ctrl+1', action: 'preset.edit', handler }]),
    )
    fireKey('1')
    expect(handler).not.toHaveBeenCalled()
  })

  it('ignores unknown combos', () => {
    const handler = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([{ combo: 'Ctrl+1', action: 'preset.edit', handler }]),
    )
    fireKey('9', { ctrl: true })
    expect(handler).not.toHaveBeenCalled()
  })

  it('skips when target is INPUT element', () => {
    const handler = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([{ combo: 'Ctrl+1', action: 'preset.edit', handler }]),
    )
    const input = document.createElement('input')
    document.body.appendChild(input)
    fireKey('1', { ctrl: true }, input)
    expect(handler).not.toHaveBeenCalled()
    document.body.removeChild(input)
  })

  it('skips when target is TEXTAREA element', () => {
    const handler = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([{ combo: 'Ctrl+1', action: 'preset.edit', handler }]),
    )
    const textarea = document.createElement('textarea')
    document.body.appendChild(textarea)
    fireKey('1', { ctrl: true }, textarea)
    expect(handler).not.toHaveBeenCalled()
    document.body.removeChild(textarea)
  })

  it('skips when target is SELECT element', () => {
    const handler = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([{ combo: 'Ctrl+1', action: 'preset.edit', handler }]),
    )
    const select = document.createElement('select')
    document.body.appendChild(select)
    fireKey('1', { ctrl: true }, select)
    expect(handler).not.toHaveBeenCalled()
    document.body.removeChild(select)
  })

  it('emits console.warn on duplicate registration and keeps first handler', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const firstHandler = vi.fn()
    const secondHandler = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([{ combo: 'Ctrl+1', action: 'first', handler: firstHandler }]),
    )
    renderHook(() =>
      useKeyboardShortcuts([{ combo: 'Ctrl+1', action: 'second', handler: secondHandler }]),
    )
    fireKey('1', { ctrl: true })
    expect(firstHandler).toHaveBeenCalledTimes(1)
    expect(secondHandler).not.toHaveBeenCalled()
    expect(warn).toHaveBeenCalled()
    expect(warn.mock.calls[0][0]).toContain('Ctrl+1')
    expect(warn.mock.calls[0][0]).toContain('first')
    expect(warn.mock.calls[0][0]).toContain('second')
  })

  it('removes bindings on unmount so a fresh registration succeeds', () => {
    const firstHandler = vi.fn()
    const secondHandler = vi.fn()
    const { unmount } = renderHook(() =>
      useKeyboardShortcuts([{ combo: 'Ctrl+1', action: 'first', handler: firstHandler }]),
    )
    unmount()
    renderHook(() =>
      useKeyboardShortcuts([{ combo: 'Ctrl+1', action: 'second', handler: secondHandler }]),
    )
    fireKey('1', { ctrl: true })
    expect(secondHandler).toHaveBeenCalledTimes(1)
    expect(firstHandler).not.toHaveBeenCalled()
  })

  it('parses Shift modifier and matches only when Shift is pressed', () => {
    const handler = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([{ combo: 'Ctrl+Shift+P', action: 'palette', handler }]),
    )
    fireKey('p', { ctrl: true })
    expect(handler).not.toHaveBeenCalled()
    fireKey('p', { ctrl: true, shift: true })
    expect(handler).toHaveBeenCalledTimes(1)
  })
})
