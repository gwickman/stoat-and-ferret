import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import RenderPage from '../RenderPage'

describe('RenderPage', () => {
  it('renders with data-testid="render-page"', () => {
    render(
      <MemoryRouter initialEntries={['/render']}>
        <RenderPage />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('render-page')).toBeDefined()
    expect(screen.getByText('Render')).toBeDefined()
  })
})
