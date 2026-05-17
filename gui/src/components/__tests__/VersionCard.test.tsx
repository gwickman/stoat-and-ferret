import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import VersionCard from '../VersionCard'
import type { VersionInfo } from '../../hooks/useVersion'

const sampleData: VersionInfo = {
  app_version: '0.1.0',
  core_version: '0.1.0',
  build_timestamp: '2026-04-22T12:00:00Z',
  git_sha: 'abc1234',
  app_sha: 'def5678',
  python_version: '3.12.0',
  database_version: '1e895699ad50',
}

describe('VersionCard', () => {
  it('renders loading state while the version payload is pending', () => {
    render(
      <VersionCard version={{ status: 'loading', data: null, error: null }} />,
    )
    expect(screen.getByText(/loading version metadata/i)).toBeDefined()
  })

  it('renders all seven fields when the payload is ready', () => {
    render(
      <VersionCard version={{ status: 'ready', data: sampleData, error: null }} />,
    )
    expect(screen.getByTestId('version-app')).toHaveTextContent('0.1.0')
    expect(screen.getByTestId('version-core')).toHaveTextContent('0.1.0')
    expect(screen.getByTestId('version-python')).toHaveTextContent('3.12.0')
    expect(screen.getByTestId('version-built')).toHaveTextContent(
      '2026-04-22T12:00:00Z',
    )
    expect(screen.getByTestId('version-app-sha')).toHaveTextContent('def5678')
    expect(screen.getByTestId('version-core-sha')).toHaveTextContent('abc1234')
    expect(screen.getByTestId('version-db-revision')).toHaveTextContent(
      '1e895699ad50',
    )
  })

  it('renders the error message when the fetch failed', () => {
    render(
      <VersionCard
        version={{ status: 'error', data: null, error: 'HTTP 500' }}
      />,
    )
    expect(screen.getByTestId('version-error')).toHaveTextContent('HTTP 500')
  })
})
