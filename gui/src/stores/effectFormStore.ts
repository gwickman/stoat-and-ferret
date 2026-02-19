import { create } from 'zustand'

/** JSON Schema property descriptor (subset relevant to our form generator). */
export interface SchemaProperty {
  type?: string
  format?: string
  enum?: string[]
  minimum?: number
  maximum?: number
  default?: unknown
  description?: string
}

/** Top-level JSON Schema for an effect's parameters. */
export interface ParameterSchema {
  type: 'object'
  properties?: Record<string, SchemaProperty>
  required?: string[]
}

interface EffectFormState {
  /** Current parameter values keyed by property name. */
  parameters: Record<string, unknown>
  /** Per-field validation error messages. */
  validationErrors: Record<string, string>
  /** The active schema driving the form. */
  schema: ParameterSchema | null
  /** Whether any parameter has been changed from its default. */
  isDirty: boolean

  setParameter: (key: string, value: unknown) => void
  setSchema: (schema: ParameterSchema) => void
  setValidationErrors: (errors: Record<string, string>) => void
  resetForm: () => void
}

/** Extract default values from a JSON schema's properties. */
function defaultsFromSchema(
  schema: ParameterSchema,
): Record<string, unknown> {
  const defaults: Record<string, unknown> = {}
  if (!schema.properties) return defaults
  for (const [key, prop] of Object.entries(schema.properties)) {
    if (prop.default !== undefined) {
      defaults[key] = prop.default
    }
  }
  return defaults
}

export const useEffectFormStore = create<EffectFormState>((set) => ({
  parameters: {},
  validationErrors: {},
  schema: null,
  isDirty: false,

  setParameter: (key, value) =>
    set((state) => ({
      parameters: { ...state.parameters, [key]: value },
      isDirty: true,
    })),

  setSchema: (schema) =>
    set({
      schema,
      parameters: defaultsFromSchema(schema),
      validationErrors: {},
      isDirty: false,
    }),

  setValidationErrors: (errors) => set({ validationErrors: errors }),

  resetForm: () =>
    set({
      parameters: {},
      validationErrors: {},
      schema: null,
      isDirty: false,
    }),
}))
