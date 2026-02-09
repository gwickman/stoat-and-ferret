import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import SearchBar from '../SearchBar'

describe('SearchBar', () => {
  it('renders with placeholder text', () => {
    render(<SearchBar value="" onChange={vi.fn()} />)

    const input = screen.getByTestId('search-bar') as HTMLInputElement
    expect(input.placeholder).toBe('Search videos...')
  })

  it('displays the current value', () => {
    render(<SearchBar value="test query" onChange={vi.fn()} />)

    const input = screen.getByTestId('search-bar') as HTMLInputElement
    expect(input.value).toBe('test query')
  })

  it('calls onChange when typing', () => {
    const onChange = vi.fn()
    render(<SearchBar value="" onChange={onChange} />)

    const input = screen.getByTestId('search-bar')
    fireEvent.change(input, { target: { value: 'new search' } })
    expect(onChange).toHaveBeenCalledWith('new search')
  })
})
