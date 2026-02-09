import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import DeleteConfirmation from '../DeleteConfirmation'

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('DeleteConfirmation', () => {
  it('does not render when closed', () => {
    render(
      <DeleteConfirmation
        open={false}
        projectId="proj-1"
        projectName="My Film"
        onClose={vi.fn()}
        onDeleted={vi.fn()}
      />,
    )
    expect(screen.queryByTestId('delete-confirmation')).toBeNull()
  })

  it('shows project name in confirmation dialog', () => {
    render(
      <DeleteConfirmation
        open={true}
        projectId="proj-1"
        projectName="My Film"
        onClose={vi.fn()}
        onDeleted={vi.fn()}
      />,
    )

    expect(screen.getByTestId('delete-confirmation')).toBeDefined()
    expect(screen.getByTestId('delete-project-name').textContent).toBe('My Film')
    expect(screen.getByTestId('btn-cancel-delete')).toBeDefined()
    expect(screen.getByTestId('btn-confirm-delete')).toBeDefined()
  })

  it('calls onClose when cancel is clicked', () => {
    const onClose = vi.fn()
    render(
      <DeleteConfirmation
        open={true}
        projectId="proj-1"
        projectName="My Film"
        onClose={onClose}
        onDeleted={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByTestId('btn-cancel-delete'))
    expect(onClose).toHaveBeenCalled()
  })

  it('calls delete API and onDeleted when confirmed', async () => {
    const onDeleted = vi.fn()
    const onClose = vi.fn()
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(null, { status: 200 }),
    )

    render(
      <DeleteConfirmation
        open={true}
        projectId="proj-1"
        projectName="My Film"
        onClose={onClose}
        onDeleted={onDeleted}
      />,
    )

    fireEvent.click(screen.getByTestId('btn-confirm-delete'))

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/v1/projects/proj-1', {
        method: 'DELETE',
      })
    })

    await waitFor(() => {
      expect(onDeleted).toHaveBeenCalled()
      expect(onClose).toHaveBeenCalled()
    })
  })

  it('shows error when delete fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response('', { status: 500 }),
    )

    render(
      <DeleteConfirmation
        open={true}
        projectId="proj-1"
        projectName="My Film"
        onClose={vi.fn()}
        onDeleted={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByTestId('btn-confirm-delete'))

    await waitFor(() => {
      expect(screen.getByTestId('delete-error')).toBeDefined()
    })
  })
})
