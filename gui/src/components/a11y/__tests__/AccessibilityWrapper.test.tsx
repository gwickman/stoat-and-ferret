import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { AccessibilityWrapper } from '../AccessibilityWrapper'

describe('AccessibilityWrapper', () => {
  it('renders skip-link as first child', () => {
    const { container } = render(
      <AccessibilityWrapper>
        <div>content</div>
      </AccessibilityWrapper>,
    )
    const first = container.firstElementChild
    expect(first?.tagName).toBe('A')
    expect(first?.textContent?.trim()).toBe('Skip to main content')
  })

  it('skip-link has href="#main-content"', () => {
    render(
      <AccessibilityWrapper>
        <div>content</div>
      </AccessibilityWrapper>,
    )
    const link = screen.getByRole('link', { name: /skip to main content/i })
    expect(link.getAttribute('href')).toBe('#main-content')
  })

  it('skip-link is hidden off-screen by default via sr-only class', () => {
    render(
      <AccessibilityWrapper>
        <div>content</div>
      </AccessibilityWrapper>,
    )
    const link = screen.getByRole('link', { name: /skip to main content/i })
    expect(link.className).toContain('sr-only')
  })

  it('polite aria-live region rendered with correct role and attributes', () => {
    render(
      <AccessibilityWrapper>
        <div>content</div>
      </AccessibilityWrapper>,
    )
    const region = screen.getByRole('status')
    expect(region.getAttribute('aria-live')).toBe('polite')
    expect(region.getAttribute('aria-atomic')).toBe('true')
    expect(region.id).toBe('announcements')
  })

  it('assertive aria-live region rendered with correct role and attributes', () => {
    render(
      <AccessibilityWrapper>
        <div>content</div>
      </AccessibilityWrapper>,
    )
    const region = screen.getByRole('alert')
    expect(region.getAttribute('aria-live')).toBe('assertive')
    expect(region.getAttribute('aria-atomic')).toBe('true')
    expect(region.id).toBe('announcements-assertive')
  })

  it('polite aria-live region is initially empty', () => {
    render(
      <AccessibilityWrapper>
        <div>content</div>
      </AccessibilityWrapper>,
    )
    const region = screen.getByRole('status')
    expect(region.textContent).toBe('')
  })

  it('assertive aria-live region is initially empty', () => {
    render(
      <AccessibilityWrapper>
        <div>content</div>
      </AccessibilityWrapper>,
    )
    const region = screen.getByRole('alert')
    expect(region.textContent).toBe('')
  })

  it('renders children after skip-link and aria-live regions', () => {
    const { container } = render(
      <AccessibilityWrapper>
        <div data-testid="child-content">hello</div>
      </AccessibilityWrapper>,
    )
    expect(screen.getByTestId('child-content')).toBeDefined()
    // Children appear after the first three elements (skip-link, polite region, assertive region)
    expect(container.children).toHaveLength(4)
  })
})
