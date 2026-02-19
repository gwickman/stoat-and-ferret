import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import EffectStack from '../EffectStack'
import type { AppliedEffect } from '../../stores/effectStackStore'

const mockEffects: AppliedEffect[] = [
  {
    effect_type: 'text_overlay',
    parameters: { text: 'Hello', fontsize: 48 },
    filter_string: 'drawtext=text=Hello:fontsize=48',
  },
  {
    effect_type: 'volume',
    parameters: { volume: 1.5 },
    filter_string: 'volume=1.5',
  },
]

describe('EffectStack', () => {
  it('renders ordered list of effects', () => {
    const onEdit = vi.fn()
    const onRemove = vi.fn()
    render(
      <EffectStack effects={mockEffects} isLoading={false} onEdit={onEdit} onRemove={onRemove} />,
    )

    expect(screen.getByTestId('effect-stack')).toBeDefined()
    expect(screen.getByTestId('effect-entry-0')).toBeDefined()
    expect(screen.getByTestId('effect-entry-1')).toBeDefined()

    // Check effect types
    expect(screen.getByTestId('effect-type-0').textContent).toBe('text_overlay')
    expect(screen.getByTestId('effect-type-1').textContent).toBe('volume')

    // Check filter strings are displayed
    expect(screen.getByTestId('effect-filter-0').textContent).toContain('drawtext')
    expect(screen.getByTestId('effect-filter-1').textContent).toContain('volume')
  })

  it('shows empty message when no effects', () => {
    render(
      <EffectStack effects={[]} isLoading={false} onEdit={vi.fn()} onRemove={vi.fn()} />,
    )

    expect(screen.getByTestId('effect-stack-empty')).toBeDefined()
    expect(screen.getByText('No effects applied to this clip.')).toBeDefined()
  })

  it('shows loading state', () => {
    render(
      <EffectStack effects={[]} isLoading={true} onEdit={vi.fn()} onRemove={vi.fn()} />,
    )

    expect(screen.getByTestId('effect-stack-loading')).toBeDefined()
  })

  it('edit button calls onEdit with index and effect', () => {
    const onEdit = vi.fn()
    render(
      <EffectStack effects={mockEffects} isLoading={false} onEdit={onEdit} onRemove={vi.fn()} />,
    )

    fireEvent.click(screen.getByTestId('edit-effect-0'))
    expect(onEdit).toHaveBeenCalledWith(0, mockEffects[0])
  })

  it('remove button shows confirmation dialog', () => {
    const onRemove = vi.fn()
    render(
      <EffectStack effects={mockEffects} isLoading={false} onEdit={vi.fn()} onRemove={onRemove} />,
    )

    // Click remove
    fireEvent.click(screen.getByTestId('remove-effect-0'))

    // Confirmation dialog appears
    expect(screen.getByTestId('confirm-delete-0')).toBeDefined()

    // Confirm deletion
    fireEvent.click(screen.getByTestId('confirm-yes-0'))
    expect(onRemove).toHaveBeenCalledWith(0)
  })

  it('cancel on confirmation dialog hides it', () => {
    render(
      <EffectStack effects={mockEffects} isLoading={false} onEdit={vi.fn()} onRemove={vi.fn()} />,
    )

    // Click remove
    fireEvent.click(screen.getByTestId('remove-effect-0'))
    expect(screen.getByTestId('confirm-delete-0')).toBeDefined()

    // Cancel
    fireEvent.click(screen.getByTestId('confirm-no-0'))
    expect(screen.queryByTestId('confirm-delete-0')).toBeNull()
  })

  it('displays key parameters in summary', () => {
    render(
      <EffectStack effects={mockEffects} isLoading={false} onEdit={vi.fn()} onRemove={vi.fn()} />,
    )

    const params = screen.getByTestId('effect-params-0')
    expect(params.textContent).toContain('text: Hello')
    expect(params.textContent).toContain('fontsize: 48')
  })
})
