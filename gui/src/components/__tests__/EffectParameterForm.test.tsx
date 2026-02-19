import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import EffectParameterForm from '../EffectParameterForm'
import type { ParameterSchema } from '../../stores/effectFormStore'
import { useEffectFormStore } from '../../stores/effectFormStore'

/** Helper: set schema in the store before rendering. */
function renderWithSchema(schema: ParameterSchema) {
  useEffectFormStore.getState().setSchema(schema)
  return render(<EffectParameterForm />)
}

beforeEach(() => {
  useEffectFormStore.getState().resetForm()
})

describe('EffectParameterForm', () => {
  it('renders nothing when no schema is set', () => {
    render(<EffectParameterForm />)
    expect(screen.queryByTestId('effect-parameter-form')).toBeNull()
  })

  it('renders a text input for string type', () => {
    renderWithSchema({
      type: 'object',
      properties: {
        text: { type: 'string', description: 'Text to display' },
      },
    })

    expect(screen.getByTestId('effect-parameter-form')).toBeDefined()
    expect(screen.getByTestId('field-text')).toBeDefined()
    const input = screen.getByTestId('input-text') as HTMLInputElement
    expect(input.type).toBe('text')
  })

  it('renders a number input for number type', () => {
    renderWithSchema({
      type: 'object',
      properties: {
        factor: { type: 'number', description: 'Speed factor' },
      },
    })

    const input = screen.getByTestId('input-factor') as HTMLInputElement
    expect(input.type).toBe('number')
  })

  it('renders range slider when number has min/max', () => {
    renderWithSchema({
      type: 'object',
      properties: {
        factor: {
          type: 'number',
          minimum: 0.25,
          maximum: 4.0,
          default: 1.0,
        },
      },
    })

    const slider = screen.getByTestId('slider-factor') as HTMLInputElement
    expect(slider.type).toBe('range')
    expect(slider.min).toBe('0.25')
    expect(slider.max).toBe('4')
  })

  it('renders a dropdown for string with enum', () => {
    renderWithSchema({
      type: 'object',
      properties: {
        fade_type: {
          type: 'string',
          enum: ['in', 'out'],
          description: 'Fade direction',
        },
      },
    })

    const select = screen.getByTestId('input-fade_type') as HTMLSelectElement
    expect(select.tagName).toBe('SELECT')
    // "Select..." placeholder + 2 enum options
    expect(select.options.length).toBe(3)
    expect(select.options[1].value).toBe('in')
    expect(select.options[2].value).toBe('out')
  })

  it('renders a checkbox for boolean type', () => {
    renderWithSchema({
      type: 'object',
      properties: {
        drop_audio: {
          type: 'boolean',
          default: false,
          description: 'Remove audio',
        },
      },
    })

    const input = screen.getByTestId('input-drop_audio') as HTMLInputElement
    expect(input.type).toBe('checkbox')
    expect(input.checked).toBe(false)
  })

  it('renders a color picker for format: "color"', () => {
    renderWithSchema({
      type: 'object',
      properties: {
        tint: { type: 'string', format: 'color', description: 'Tint color' },
      },
    })

    const input = screen.getByTestId('input-tint') as HTMLInputElement
    expect(input.type).toBe('color')
  })

  it('pre-populates default values from schema', () => {
    renderWithSchema({
      type: 'object',
      properties: {
        fontsize: { type: 'number', default: 48 },
        position: {
          type: 'string',
          enum: ['center', 'bottom_center'],
          default: 'bottom_center',
        },
        drop_audio: { type: 'boolean', default: true },
      },
    })

    const fontsizeInput = screen.getByTestId(
      'input-fontsize',
    ) as HTMLInputElement
    expect(Number(fontsizeInput.value)).toBe(48)

    const positionSelect = screen.getByTestId(
      'input-position',
    ) as HTMLSelectElement
    expect(positionSelect.value).toBe('bottom_center')

    const checkboxInput = screen.getByTestId(
      'input-drop_audio',
    ) as HTMLInputElement
    expect(checkboxInput.checked).toBe(true)
  })

  it('displays validation errors inline', () => {
    useEffectFormStore.getState().setSchema({
      type: 'object',
      properties: {
        factor: { type: 'number', description: 'Speed factor' },
        text: { type: 'string', description: 'Text to display' },
      },
    })
    useEffectFormStore.getState().setValidationErrors({
      factor: 'Value must be between 0.25 and 4.0',
      text: 'Required field',
    })

    render(<EffectParameterForm />)

    expect(screen.getByTestId('error-factor').textContent).toBe(
      'Value must be between 0.25 and 4.0',
    )
    expect(screen.getByTestId('error-text').textContent).toBe('Required field')
  })

  it('clears validation errors when schema is reset', () => {
    useEffectFormStore.getState().setSchema({
      type: 'object',
      properties: {
        text: { type: 'string' },
      },
    })
    useEffectFormStore.getState().setValidationErrors({
      text: 'Required',
    })

    // Reset by setting a new schema
    useEffectFormStore.getState().setSchema({
      type: 'object',
      properties: {
        text: { type: 'string' },
      },
    })

    expect(useEffectFormStore.getState().validationErrors).toEqual({})
  })

  it('onChange updates store parameter value', () => {
    renderWithSchema({
      type: 'object',
      properties: {
        text: { type: 'string', description: 'Text to display' },
      },
    })

    const input = screen.getByTestId('input-text') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'Hello World' } })

    expect(useEffectFormStore.getState().parameters.text).toBe('Hello World')
    expect(useEffectFormStore.getState().isDirty).toBe(true)
  })

  it('number onChange updates store with numeric value', () => {
    renderWithSchema({
      type: 'object',
      properties: {
        factor: { type: 'number', minimum: 0.25, maximum: 4.0 },
      },
    })

    const input = screen.getByTestId('input-factor') as HTMLInputElement
    fireEvent.change(input, { target: { value: '2.5' } })

    expect(useEffectFormStore.getState().parameters.factor).toBe(2.5)
  })

  it('boolean onChange updates store', () => {
    renderWithSchema({
      type: 'object',
      properties: {
        normalize: { type: 'boolean', default: false },
      },
    })

    const input = screen.getByTestId('input-normalize') as HTMLInputElement
    fireEvent.click(input)

    expect(useEffectFormStore.getState().parameters.normalize).toBe(true)
  })

  it('renders fields in schema property order', () => {
    renderWithSchema({
      type: 'object',
      properties: {
        alpha: { type: 'string' },
        beta: { type: 'number' },
        gamma: { type: 'boolean' },
      },
    })

    const fields = screen.getAllByTestId(/^field-/)
    expect(fields[0].getAttribute('data-testid')).toBe('field-alpha')
    expect(fields[1].getAttribute('data-testid')).toBe('field-beta')
    expect(fields[2].getAttribute('data-testid')).toBe('field-gamma')
  })
})

describe('effectFormStore', () => {
  it('initializes parameters from schema defaults', () => {
    useEffectFormStore.getState().setSchema({
      type: 'object',
      properties: {
        fontsize: { type: 'number', default: 48 },
        text: { type: 'string' },
      },
    })

    const state = useEffectFormStore.getState()
    expect(state.parameters.fontsize).toBe(48)
    expect(state.parameters.text).toBeUndefined()
    expect(state.isDirty).toBe(false)
  })

  it('stores and retrieves validation errors', () => {
    useEffectFormStore.getState().setValidationErrors({
      text: 'Required',
      fontsize: 'Out of range',
    })

    const state = useEffectFormStore.getState()
    expect(state.validationErrors.text).toBe('Required')
    expect(state.validationErrors.fontsize).toBe('Out of range')
  })

  it('resetForm clears all state', () => {
    useEffectFormStore.getState().setSchema({
      type: 'object',
      properties: { x: { type: 'number', default: 5 } },
    })
    useEffectFormStore.getState().setParameter('x', 10)
    useEffectFormStore.getState().setValidationErrors({ x: 'err' })

    useEffectFormStore.getState().resetForm()

    const state = useEffectFormStore.getState()
    expect(state.schema).toBeNull()
    expect(state.parameters).toEqual({})
    expect(state.validationErrors).toEqual({})
    expect(state.isDirty).toBe(false)
  })
})
