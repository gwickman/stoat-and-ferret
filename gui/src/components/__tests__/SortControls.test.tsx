import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import SortControls from '../SortControls'

describe('SortControls', () => {
  it('renders sort field dropdown with options', () => {
    render(
      <SortControls
        sortField="date"
        sortOrder="desc"
        onSortFieldChange={vi.fn()}
        onSortOrderChange={vi.fn()}
      />,
    )

    const select = screen.getByTestId('sort-field') as HTMLSelectElement
    expect(select.value).toBe('date')

    const options = select.querySelectorAll('option')
    expect(options.length).toBe(3)
    expect(options[0].value).toBe('date')
    expect(options[1].value).toBe('name')
    expect(options[2].value).toBe('duration')
  })

  it('calls onSortFieldChange when selecting a field', () => {
    const onSortFieldChange = vi.fn()
    render(
      <SortControls
        sortField="date"
        sortOrder="desc"
        onSortFieldChange={onSortFieldChange}
        onSortOrderChange={vi.fn()}
      />,
    )

    const select = screen.getByTestId('sort-field')
    fireEvent.change(select, { target: { value: 'name' } })
    expect(onSortFieldChange).toHaveBeenCalledWith('name')
  })

  it('toggles sort order when clicking order button', () => {
    const onSortOrderChange = vi.fn()
    render(
      <SortControls
        sortField="date"
        sortOrder="desc"
        onSortFieldChange={vi.fn()}
        onSortOrderChange={onSortOrderChange}
      />,
    )

    const orderBtn = screen.getByTestId('sort-order')
    fireEvent.click(orderBtn)
    expect(onSortOrderChange).toHaveBeenCalledWith('asc')
  })

  it('toggles from asc to desc', () => {
    const onSortOrderChange = vi.fn()
    render(
      <SortControls
        sortField="date"
        sortOrder="asc"
        onSortFieldChange={vi.fn()}
        onSortOrderChange={onSortOrderChange}
      />,
    )

    const orderBtn = screen.getByTestId('sort-order')
    fireEvent.click(orderBtn)
    expect(onSortOrderChange).toHaveBeenCalledWith('desc')
  })
})
