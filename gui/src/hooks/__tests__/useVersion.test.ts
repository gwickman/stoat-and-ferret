import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useVersion } from '../useVersion'

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('useVersion', () => {
  it('resolves to ready with payload on 200 OK', async () => {
    const payload = {
      app_version: '0.1.0',
      core_version: '0.1.0',
      build_timestamp: '2026-04-22T12:00:00Z',
      git_sha: 'abc1234',
      app_sha: 'def5678',
      python_version: '3.12.0',
      database_version: '1e895699ad50',
    }
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(payload), { status: 200 }),
    )

    const { result } = renderHook(() => useVersion())

    await waitFor(() => {
      expect(result.current.status).toBe('ready')
    })
    expect(result.current.data).toEqual(payload)
  })

  it('surfaces a non-ok HTTP status as an error state', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('oops', { status: 500 }),
    )

    const { result } = renderHook(() => useVersion())

    await waitFor(() => {
      expect(result.current.status).toBe('error')
    })
    expect(result.current.error).toContain('500')
  })

  it('surfaces a network error as an error state', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('boom'))

    const { result } = renderHook(() => useVersion())

    await waitFor(() => {
      expect(result.current.status).toBe('error')
    })
    expect(result.current.error).toBe('boom')
  })
})
