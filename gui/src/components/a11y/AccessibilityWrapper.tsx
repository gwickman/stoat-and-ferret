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
      <output aria-atomic="true" aria-live="polite" id="announcements" />
      <div role="alert" aria-atomic="true" aria-live="assertive" id="announcements-assertive" />
      {children}
    </>
  )
}
