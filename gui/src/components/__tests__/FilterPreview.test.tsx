import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import FilterPreview, { highlightFilter } from '../FilterPreview'
import { useEffectPreviewStore } from '../../stores/effectPreviewStore'

beforeEach(() => {
  useEffectPreviewStore.getState().reset()
})

describe('FilterPreview', () => {
  it('renders nothing when no filter string, not loading, and no error', () => {
    render(<FilterPreview />)
    expect(screen.queryByTestId('filter-preview')).toBeNull()
  })

  it('renders filter string in monospace pre element', () => {
    useEffectPreviewStore.getState().setFilterString('volume=0.8')

    render(<FilterPreview />)

    const pre = screen.getByTestId('filter-string')
    expect(pre).toBeDefined()
    expect(pre.tagName).toBe('PRE')
    expect(pre.textContent).toContain('volume=0.8')
  })

  it('shows loading indicator when isLoading is true', () => {
    useEffectPreviewStore.getState().setLoading(true)

    render(<FilterPreview />)

    expect(screen.getByTestId('preview-loading')).toBeDefined()
    expect(screen.getByTestId('preview-loading').textContent).toContain(
      'Generating preview',
    )
  })

  it('shows error state when error is set', () => {
    useEffectPreviewStore.getState().setError('Preview failed: 400')

    render(<FilterPreview />)

    expect(screen.getByTestId('preview-error')).toBeDefined()
    expect(screen.getByTestId('preview-error').textContent).toContain(
      'Preview failed: 400',
    )
  })

  it('copies filter string to clipboard on button click', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, {
      clipboard: { writeText },
    })

    useEffectPreviewStore.getState().setFilterString('fade=t=in:d=1.5')

    render(<FilterPreview />)

    const button = screen.getByTestId('copy-button')
    fireEvent.click(button)

    expect(writeText).toHaveBeenCalledWith('fade=t=in:d=1.5')
  })

  it('shows "Copied!" feedback after copy', async () => {
    vi.useFakeTimers()
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    })

    useEffectPreviewStore.getState().setFilterString('volume=0.8')

    render(<FilterPreview />)

    const button = screen.getByTestId('copy-button')
    expect(button.textContent).toBe('Copy')

    await fireEvent.click(button)
    // After microtask for the async handleCopy
    await vi.advanceTimersByTimeAsync(0)
    expect(screen.getByTestId('copy-button').textContent).toBe('Copied!')

    vi.useRealTimers()
  })
})

describe('highlightFilter', () => {
  it('highlights filter names in the string', () => {
    const { container } = render(<span>{highlightFilter('volume=0.8')}</span>)
    const filterName = container.querySelector('[data-testid="filter-name"]')
    expect(filterName).toBeDefined()
    expect(filterName!.textContent).toBe('volume')
  })

  it('highlights pad labels in the string', () => {
    const { container } = render(
      <span>{highlightFilter('[0:v]fade=t=in:d=1.5[out]')}</span>,
    )
    const padLabels = container.querySelectorAll('[data-testid="pad-label"]')
    expect(padLabels.length).toBe(2)
    expect(padLabels[0].textContent).toBe('[0:v]')
    expect(padLabels[1].textContent).toBe('[out]')
  })

  it('handles string with both filter names and pad labels', () => {
    const { container } = render(
      <span>
        {highlightFilter('[speech]asplit[sc][speech_out]')}
      </span>,
    )
    const filterNames = container.querySelectorAll(
      '[data-testid="filter-name"]',
    )
    const padLabels = container.querySelectorAll('[data-testid="pad-label"]')
    expect(filterNames.length).toBe(1)
    expect(filterNames[0].textContent).toBe('asplit')
    expect(padLabels.length).toBe(3)
  })

  it('returns plain text when no patterns match', () => {
    const result = highlightFilter('some_unknown_filter=abc')
    expect(result).toHaveLength(1)
    expect(result[0]).toBe('some_unknown_filter=abc')
  })
})
