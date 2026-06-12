import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import RazorTool from '../RazorTool'

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('RazorTool', () => {
  it('renders split button with correct aria-label', () => {
    render(
      <RazorTool
        projectId="proj-1"
        clipId="clip-1"
        splitFrame={60}
      />,
    )
    expect(screen.getByTestId('razor-tool-button')).toBeDefined()
    const btn = screen.getByTestId('razor-tool-button')
    expect(btn.getAttribute('aria-label')).toBe('Split clip at frame 60')
  })

  it('is disabled when disabled prop is true', () => {
    render(
      <RazorTool
        projectId="proj-1"
        clipId="clip-1"
        splitFrame={60}
        disabled={true}
      />,
    )
    const btn = screen.getByTestId('razor-tool-button') as HTMLButtonElement
    expect(btn.disabled).toBe(true)
  })

  it('calls POST /split and invokes onSplitComplete on success', async () => {
    const onSplitComplete = vi.fn()
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(
        JSON.stringify({ clip_a: { id: 'clip-a' }, clip_b: { id: 'clip-b' } }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    render(
      <RazorTool
        projectId="proj-1"
        clipId="clip-1"
        splitFrame={60}
        onSplitComplete={onSplitComplete}
      />,
    )

    fireEvent.click(screen.getByTestId('razor-tool-button'))

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        '/api/v1/projects/proj-1/clips/clip-1/split',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ split_frame: 60 }),
        }),
      )
    })

    await waitFor(() => {
      expect(onSplitComplete).toHaveBeenCalledWith('clip-a', 'clip-b')
    })
  })

  it('shows error message on invalid split frame (422)', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          detail: { error: 'invalid_split_frame', valid_range: [1, 99] },
        }),
        { status: 422, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    render(
      <RazorTool
        projectId="proj-1"
        clipId="clip-1"
        splitFrame={0}
      />,
    )

    fireEvent.click(screen.getByTestId('razor-tool-button'))

    await waitFor(() => {
      expect(screen.getByTestId('razor-tool-error')).toBeDefined()
      expect(screen.getByTestId('razor-tool-error').textContent).toContain(
        'Split frame 0 is outside clip bounds',
      )
    })
  })

  it('shows generic error on non-422 failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response('{}', {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    render(
      <RazorTool
        projectId="proj-1"
        clipId="clip-1"
        splitFrame={50}
      />,
    )

    fireEvent.click(screen.getByTestId('razor-tool-button'))

    await waitFor(() => {
      expect(screen.getByTestId('razor-tool-error').textContent).toContain('Split failed: 500')
    })
  })
})
