import React from 'react'

interface AccessibilityWrapperProps {
  children: React.ReactNode
}

export function AccessibilityWrapper({ children }: AccessibilityWrapperProps): React.ReactElement {
  return (
    <>
      <a href="#main-content" className="sr-only focus:not-sr-only">
        Skip to main content
      </a>
      <div role="status" aria-atomic="true" aria-live="polite" id="announcements" />
      <div role="alert" aria-atomic="true" aria-live="assertive" id="announcements-assertive" />
      {children}
    </>
  )
}
