import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import DirectoryBrowser from '../DirectoryBrowser'

const mockDirectories = {
  path: '/home/user',
  directories: [
    { name: 'Documents', path: '/home/user/Documents' },
    { name: 'Videos', path: '/home/user/Videos' },
  ],
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('DirectoryBrowser', () => {
  it('renders loading state initially', () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      () => new Promise(() => {}), // never resolves
    )

    render(
      <DirectoryBrowser onSelect={vi.fn()} onCancel={vi.fn()} />,
    )

    expect(screen.getByTestId('directory-browser-loading')).toBeDefined()
  })

  it('renders directory list after loading', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify(mockDirectories), { status: 200 }),
    )

    render(
      <DirectoryBrowser onSelect={vi.fn()} onCancel={vi.fn()} />,
    )

    await waitFor(() => {
      expect(screen.getByTestId('directory-browser-list')).toBeDefined()
    })

    const entries = screen.getAllByTestId('directory-browser-entry')
    expect(entries).toHaveLength(2)
    expect(entries[0].textContent).toContain('Documents')
    expect(entries[1].textContent).toContain('Videos')
  })

  it('renders empty state when directory has no subdirectories', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(
        JSON.stringify({ path: '/home/user/empty', directories: [] }),
        { status: 200 },
      ),
    )

    render(
      <DirectoryBrowser
        onSelect={vi.fn()}
        onCancel={vi.fn()}
        initialPath="/home/user/empty"
      />,
    )

    await waitFor(() => {
      expect(screen.getByTestId('directory-browser-empty')).toBeDefined()
    })

    expect(screen.getByTestId('directory-browser-empty').textContent).toBe(
      'No subdirectories',
    )
  })

  it('calls onSelect with current path when Select button clicked', async () => {
    const onSelect = vi.fn()
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify(mockDirectories), { status: 200 }),
    )

    render(
      <DirectoryBrowser onSelect={onSelect} onCancel={vi.fn()} />,
    )

    await waitFor(() => {
      expect(screen.getByTestId('directory-browser-list')).toBeDefined()
    })

    fireEvent.click(screen.getByTestId('directory-browser-select'))
    expect(onSelect).toHaveBeenCalledWith('/home/user')
  })

  it('navigates into subdirectory on click, triggering new fetch', async () => {
    const subDirResponse = {
      path: '/home/user/Videos',
      directories: [
        { name: 'Movies', path: '/home/user/Videos/Movies' },
      ],
    }

    const fetchSpy = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(
        new Response(JSON.stringify(mockDirectories), { status: 200 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify(subDirResponse), { status: 200 }),
      )

    render(
      <DirectoryBrowser onSelect={vi.fn()} onCancel={vi.fn()} />,
    )

    await waitFor(() => {
      expect(screen.getByTestId('directory-browser-list')).toBeDefined()
    })

    // Click on "Videos" to navigate into it
    const entries = screen.getAllByTestId('directory-browser-entry')
    const videosEntry = entries.find((e) => e.textContent?.includes('Videos'))
    expect(videosEntry).toBeDefined()
    fireEvent.click(videosEntry!)

    // Should trigger a second fetch for the subdirectory
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledTimes(2)
    })

    // Should now show the subdirectory contents
    await waitFor(() => {
      const newEntries = screen.getAllByTestId('directory-browser-entry')
      expect(newEntries).toHaveLength(1)
      expect(newEntries[0].textContent).toContain('Movies')
    })

    // Path display should be updated
    expect(screen.getByTestId('directory-browser-path').textContent).toBe(
      '/home/user/Videos',
    )
  })

  it('calls onCancel when Cancel button clicked', async () => {
    const onCancel = vi.fn()
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify(mockDirectories), { status: 200 }),
    )

    render(
      <DirectoryBrowser onSelect={vi.fn()} onCancel={onCancel} />,
    )

    await waitFor(() => {
      expect(screen.getByTestId('directory-browser-list')).toBeDefined()
    })

    fireEvent.click(screen.getByTestId('directory-browser-cancel'))
    expect(onCancel).toHaveBeenCalled()
  })

  it('shows error state on fetch failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(
        JSON.stringify({ detail: { message: 'Path not allowed' } }),
        { status: 403 },
      ),
    )

    render(
      <DirectoryBrowser
        onSelect={vi.fn()}
        onCancel={vi.fn()}
        initialPath="/restricted"
      />,
    )

    await waitFor(() => {
      expect(screen.getByTestId('directory-browser-error')).toBeDefined()
    })

    expect(screen.getByTestId('directory-browser-error').textContent).toBe(
      'Path not allowed',
    )
  })
})
