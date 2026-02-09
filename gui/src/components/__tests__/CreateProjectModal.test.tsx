import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import CreateProjectModal from '../CreateProjectModal'

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('CreateProjectModal', () => {
  it('does not render when closed', () => {
    render(
      <CreateProjectModal open={false} onClose={vi.fn()} onCreated={vi.fn()} />,
    )
    expect(screen.queryByTestId('create-project-modal')).toBeNull()
  })

  it('renders form fields when open', () => {
    render(
      <CreateProjectModal open={true} onClose={vi.fn()} onCreated={vi.fn()} />,
    )
    expect(screen.getByTestId('create-project-modal')).toBeDefined()
    expect(screen.getByTestId('input-project-name')).toBeDefined()
    expect(screen.getByTestId('input-resolution')).toBeDefined()
    expect(screen.getByTestId('input-fps')).toBeDefined()
    expect(screen.getByTestId('btn-create')).toBeDefined()
    expect(screen.getByTestId('btn-cancel')).toBeDefined()
  })

  it('shows error when name is empty', async () => {
    render(
      <CreateProjectModal open={true} onClose={vi.fn()} onCreated={vi.fn()} />,
    )

    fireEvent.click(screen.getByTestId('btn-create'))

    await waitFor(() => {
      expect(screen.getByTestId('error-name')).toBeDefined()
      expect(screen.getByTestId('error-name').textContent).toBe(
        'Project name is required',
      )
    })
  })

  it('shows error for invalid resolution', async () => {
    render(
      <CreateProjectModal open={true} onClose={vi.fn()} onCreated={vi.fn()} />,
    )

    const nameInput = screen.getByTestId('input-project-name')
    fireEvent.change(nameInput, { target: { value: 'Test' } })

    const resInput = screen.getByTestId('input-resolution')
    fireEvent.change(resInput, { target: { value: 'bad' } })

    fireEvent.click(screen.getByTestId('btn-create'))

    await waitFor(() => {
      expect(screen.getByTestId('error-resolution')).toBeDefined()
      expect(screen.getByTestId('error-resolution').textContent).toBe(
        'Enter a valid resolution (e.g., 1920x1080)',
      )
    })
  })

  it('shows error for invalid fps', async () => {
    render(
      <CreateProjectModal open={true} onClose={vi.fn()} onCreated={vi.fn()} />,
    )

    fireEvent.change(screen.getByTestId('input-project-name'), {
      target: { value: 'Test' },
    })
    fireEvent.change(screen.getByTestId('input-fps'), {
      target: { value: '0' },
    })

    // Submit form directly
    const form = screen.getByTestId('create-project-modal').querySelector('form')!
    fireEvent.submit(form)

    await waitFor(() => {
      expect(screen.getByTestId('error-fps')).toBeDefined()
      expect(screen.getByTestId('error-fps').textContent).toBe(
        'FPS must be between 1 and 120',
      )
    })
  })

  it('submits valid form and calls API', async () => {
    const onCreated = vi.fn()
    const onClose = vi.fn()
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: 'proj-1',
          name: 'Test Project',
          output_width: 1920,
          output_height: 1080,
          output_fps: 30,
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-01T00:00:00Z',
        }),
        { status: 201 },
      ),
    )

    render(
      <CreateProjectModal open={true} onClose={onClose} onCreated={onCreated} />,
    )

    fireEvent.change(screen.getByTestId('input-project-name'), {
      target: { value: 'Test Project' },
    })

    fireEvent.click(screen.getByTestId('btn-create'))

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/v1/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'Test Project',
          output_width: 1920,
          output_height: 1080,
          output_fps: 30,
        }),
      })
    })

    await waitFor(() => {
      expect(onCreated).toHaveBeenCalled()
      expect(onClose).toHaveBeenCalled()
    })
  })

  it('clears errors when valid input is entered', async () => {
    render(
      <CreateProjectModal open={true} onClose={vi.fn()} onCreated={vi.fn()} />,
    )

    // Trigger validation
    fireEvent.click(screen.getByTestId('btn-create'))

    await waitFor(() => {
      expect(screen.getByTestId('error-name')).toBeDefined()
    })

    // Fix the input
    fireEvent.change(screen.getByTestId('input-project-name'), {
      target: { value: 'Fixed' },
    })

    expect(screen.queryByTestId('error-name')).toBeNull()
  })
})
