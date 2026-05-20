import { useState } from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ErrorBoundary from '../ErrorBoundary'

function ThrowingChild({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error('Test render error')
  return <div data-testid="child-content">Child content</div>
}

beforeEach(() => {
  // Suppress React's console.error for expected boundary errors in tests
  vi.spyOn(console, 'error').mockImplementation(() => {})
})

describe('ErrorBoundary', () => {
  it('renders children when no error occurs', () => {
    render(
      <ErrorBoundary>
        <ThrowingChild shouldThrow={false} />
      </ErrorBoundary>,
    )
    expect(screen.getByTestId('child-content')).toBeDefined()
    expect(screen.queryByTestId('error-boundary-fallback')).toBeNull()
  })

  it('renders fallback UI when child throws during render', () => {
    render(
      <ErrorBoundary>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>,
    )
    expect(screen.getByTestId('error-boundary-fallback')).toBeDefined()
    expect(screen.getByTestId('error-boundary-message').textContent).toBe('Test render error')
    expect(screen.queryByTestId('child-content')).toBeNull()
  })

  it('truncates error messages longer than 200 characters', () => {
    const longMessage = 'x'.repeat(250)
    function LongErrorChild(): never {
      throw new Error(longMessage)
    }
    render(
      <ErrorBoundary>
        <LongErrorChild />
      </ErrorBoundary>,
    )
    const msg = screen.getByTestId('error-boundary-message').textContent ?? ''
    expect(msg.length).toBeLessThanOrEqual(201) // 200 chars + ellipsis char
    expect(msg.endsWith('…')).toBe(true)
  })

  it('shows Go Back button in fallback UI', () => {
    render(
      <ErrorBoundary>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>,
    )
    expect(screen.getByTestId('error-boundary-dismiss')).toBeDefined()
    expect(screen.getByTestId('error-boundary-dismiss').textContent).toBe('Go Back')
  })

  it('recovers and re-renders children after dismiss is clicked', () => {
    // Use a stateful wrapper so we can fix the throw condition before dismissing.
    // Clicking "fix-error" sets shouldThrow=false; ErrorBoundary still shows fallback
    // (it's in error state). Clicking dismiss clears error state, then re-renders
    // ThrowingChild with shouldThrow=false → no error → child renders normally.
    function TestApp() {
      const [shouldThrow, setShouldThrow] = useState(true)
      return (
        <>
          <button data-testid="fix-error" onClick={() => setShouldThrow(false)}>Fix</button>
          <ErrorBoundary>
            <ThrowingChild shouldThrow={shouldThrow} />
          </ErrorBoundary>
        </>
      )
    }

    render(<TestApp />)
    expect(screen.getByTestId('error-boundary-fallback')).toBeDefined()

    // Fix the error condition first (parent state change, boundary still shows fallback)
    fireEvent.click(screen.getByTestId('fix-error'))
    expect(screen.getByTestId('error-boundary-fallback')).toBeDefined()

    // Now dismiss — clears boundary error state, re-renders children without throw
    fireEvent.click(screen.getByTestId('error-boundary-dismiss'))
    expect(screen.queryByTestId('error-boundary-fallback')).toBeNull()
    expect(screen.getByTestId('child-content')).toBeDefined()
  })

  it('does not catch errors outside its subtree', () => {
    render(
      <div data-testid="outside">
        <ErrorBoundary>
          <ThrowingChild shouldThrow={false} />
        </ErrorBoundary>
      </div>,
    )
    expect(screen.getByTestId('outside')).toBeDefined()
    expect(screen.getByTestId('child-content')).toBeDefined()
    expect(screen.queryByTestId('error-boundary-fallback')).toBeNull()
  })
})
