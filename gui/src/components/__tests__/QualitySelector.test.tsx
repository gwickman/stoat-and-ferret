import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { usePreviewStore } from '../../stores/previewStore'
import { useProjectStore } from '../../stores/projectStore'
import QualitySelector from '../QualitySelector'

beforeEach(() => {
  usePreviewStore.setState({
    quality: 'medium',
    status: null,
    sessionId: null,
  })
  useProjectStore.setState({ selectedProjectId: 'proj-1' })
})

describe('QualitySelector', () => {
  it('renders dropdown with low, medium, high options', () => {
    render(<QualitySelector />)
    const select = screen.getByTestId('quality-select') as HTMLSelectElement
    const options = Array.from(select.options).map((o) => o.value)
    expect(options).toEqual(['low', 'medium', 'high'])
  })

  it('shows current quality as selected value', () => {
    usePreviewStore.setState({ quality: 'high' })
    render(<QualitySelector />)
    const select = screen.getByTestId('quality-select') as HTMLSelectElement
    expect(select.value).toBe('high')
  })

  it('calls setQuality with project ID and new quality on change', () => {
    const setQuality = vi.fn()
    usePreviewStore.setState({ setQuality })

    render(<QualitySelector />)
    const select = screen.getByTestId('quality-select')
    fireEvent.change(select, { target: { value: 'low' } })

    expect(setQuality).toHaveBeenCalledWith('proj-1', 'low')
  })

  it('does not call setQuality when selecting the same quality', () => {
    const setQuality = vi.fn()
    usePreviewStore.setState({ quality: 'medium', setQuality })

    render(<QualitySelector />)
    fireEvent.change(screen.getByTestId('quality-select'), {
      target: { value: 'medium' },
    })

    expect(setQuality).not.toHaveBeenCalled()
  })

  it('is disabled during generating status', () => {
    usePreviewStore.setState({ status: 'generating' })
    render(<QualitySelector />)
    const select = screen.getByTestId('quality-select') as HTMLSelectElement
    expect(select.disabled).toBe(true)
  })

  it('is disabled during initializing status', () => {
    usePreviewStore.setState({ status: 'initializing' })
    render(<QualitySelector />)
    const select = screen.getByTestId('quality-select') as HTMLSelectElement
    expect(select.disabled).toBe(true)
  })

  it('is enabled when status is ready', () => {
    usePreviewStore.setState({ status: 'ready' })
    render(<QualitySelector />)
    const select = screen.getByTestId('quality-select') as HTMLSelectElement
    expect(select.disabled).toBe(false)
  })
})
