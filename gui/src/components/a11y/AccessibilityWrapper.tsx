import React from 'react'

interface AccessibilityWrapperProps {
  readonly children: React.ReactNode
}

export function AccessibilityWrapper({ children }: Readonly<AccessibilityWrapperProps>): React.ReactElement {
  return (
    <>
      <a href="#main-content" className="sr-only focus:not-sr-only">
        Skip to main content
      </a>
      {/* eslint-disable-next-line jsx-a11y/prefer-tag-over-role -- Live region anchor; the explicit role="status" attribute is checked by e2e tests and required by screen readers that query the DOM attribute */}
      <div role="status" aria-atomic="true" aria-live="polite" id="announcements" />
      <div role="alert" aria-atomic="true" aria-live="assertive" id="announcements-assertive" />
      {children}
    </>
  )
}
