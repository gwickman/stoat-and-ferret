import type { SchemaProperty } from '../stores/effectFormStore'
import { useEffectFormStore } from '../stores/effectFormStore'

/** Derive a human-readable label from a schema property key. */
function labelFor(key: string, prop: SchemaProperty): string {
  return prop.description ?? key.replace(/_/g, ' ')
}

function NumberField({
  name,
  prop,
  value,
  error,
  onChange,
}: {
  name: string
  prop: SchemaProperty
  value: unknown
  error?: string
  onChange: (key: string, value: unknown) => void
}) {
  const hasRange = prop.minimum !== undefined && prop.maximum !== undefined
  const numValue = typeof value === 'number' ? value : 0
  const label = labelFor(name, prop)

  return (
    <div className="mb-3" data-testid={`field-${name}`}>
      <label
        htmlFor={`param-${name}`}
        className="mb-1 block text-sm font-medium text-gray-300"
      >
        {label}
      </label>
      <div className="flex items-center gap-2">
        {hasRange && (
          <input
            type="range"
            min={prop.minimum}
            max={prop.maximum}
            step="any"
            value={numValue}
            onChange={(e) => onChange(name, Number(e.target.value))}
            className="flex-1"
            aria-label={`${label} slider`}
            data-testid={`slider-${name}`}
          />
        )}
        <input
          id={`param-${name}`}
          type="number"
          min={prop.minimum}
          max={prop.maximum}
          step="any"
          value={numValue}
          onChange={(e) => onChange(name, Number(e.target.value))}
          className="w-24 rounded border border-gray-600 bg-gray-800 px-2 py-1 text-sm text-white"
          data-testid={`input-${name}`}
        />
      </div>
      {error && (
        <p className="mt-1 text-xs text-red-400" data-testid={`error-${name}`}>
          {error}
        </p>
      )}
    </div>
  )
}

function StringField({
  name,
  prop,
  value,
  error,
  onChange,
}: {
  name: string
  prop: SchemaProperty
  value: unknown
  error?: string
  onChange: (key: string, value: unknown) => void
}) {
  const label = labelFor(name, prop)

  return (
    <div className="mb-3" data-testid={`field-${name}`}>
      <label
        htmlFor={`param-${name}`}
        className="mb-1 block text-sm font-medium text-gray-300"
      >
        {label}
      </label>
      <input
        id={`param-${name}`}
        type="text"
        value={typeof value === 'string' ? value : ''}
        onChange={(e) => onChange(name, e.target.value)}
        placeholder={prop.description}
        className="w-full rounded border border-gray-600 bg-gray-800 px-2 py-1 text-sm text-white placeholder-gray-500"
        data-testid={`input-${name}`}
      />
      {error && (
        <p className="mt-1 text-xs text-red-400" data-testid={`error-${name}`}>
          {error}
        </p>
      )}
    </div>
  )
}

function EnumField({
  name,
  prop,
  value,
  error,
  onChange,
}: {
  name: string
  prop: SchemaProperty
  value: unknown
  error?: string
  onChange: (key: string, value: unknown) => void
}) {
  const label = labelFor(name, prop)

  return (
    <div className="mb-3" data-testid={`field-${name}`}>
      <label
        htmlFor={`param-${name}`}
        className="mb-1 block text-sm font-medium text-gray-300"
      >
        {label}
      </label>
      <select
        id={`param-${name}`}
        value={typeof value === 'string' ? value : ''}
        onChange={(e) => onChange(name, e.target.value)}
        className="w-full rounded border border-gray-600 bg-gray-800 px-2 py-1 text-sm text-white"
        data-testid={`input-${name}`}
      >
        <option value="">Select...</option>
        {prop.enum?.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
      {error && (
        <p className="mt-1 text-xs text-red-400" data-testid={`error-${name}`}>
          {error}
        </p>
      )}
    </div>
  )
}

function BooleanField({
  name,
  prop,
  value,
  error,
  onChange,
}: {
  name: string
  prop: SchemaProperty
  value: unknown
  error?: string
  onChange: (key: string, value: unknown) => void
}) {
  const label = labelFor(name, prop)

  return (
    <div className="mb-3" data-testid={`field-${name}`}>
      <label className="flex items-center gap-2 text-sm font-medium text-gray-300">
        <input
          id={`param-${name}`}
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onChange(name, e.target.checked)}
          className="rounded border-gray-600 bg-gray-800"
          data-testid={`input-${name}`}
        />
        {label}
      </label>
      {error && (
        <p className="mt-1 text-xs text-red-400" data-testid={`error-${name}`}>
          {error}
        </p>
      )}
    </div>
  )
}

function ColorField({
  name,
  prop,
  value,
  error,
  onChange,
}: {
  name: string
  prop: SchemaProperty
  value: unknown
  error?: string
  onChange: (key: string, value: unknown) => void
}) {
  const label = labelFor(name, prop)

  return (
    <div className="mb-3" data-testid={`field-${name}`}>
      <label
        htmlFor={`param-${name}`}
        className="mb-1 block text-sm font-medium text-gray-300"
      >
        {label}
      </label>
      <input
        id={`param-${name}`}
        type="color"
        value={typeof value === 'string' ? value : '#000000'}
        onChange={(e) => onChange(name, e.target.value)}
        className="h-8 w-16 cursor-pointer rounded border border-gray-600 bg-gray-800"
        data-testid={`input-${name}`}
      />
      {error && (
        <p className="mt-1 text-xs text-red-400" data-testid={`error-${name}`}>
          {error}
        </p>
      )}
    </div>
  )
}

/** Render the appropriate field component for a schema property. */
function SchemaField({
  name,
  prop,
  value,
  error,
  onChange,
}: {
  name: string
  prop: SchemaProperty
  value: unknown
  error?: string
  onChange: (key: string, value: unknown) => void
}) {
  // Color picker: format: "color"
  if (prop.format === 'color') {
    return (
      <ColorField
        name={name}
        prop={prop}
        value={value}
        error={error}
        onChange={onChange}
      />
    )
  }

  // Enum dropdown: string with enum array
  if (prop.type === 'string' && prop.enum) {
    return (
      <EnumField
        name={name}
        prop={prop}
        value={value}
        error={error}
        onChange={onChange}
      />
    )
  }

  switch (prop.type) {
    case 'number':
    case 'integer':
      return (
        <NumberField
          name={name}
          prop={prop}
          value={value}
          error={error}
          onChange={onChange}
        />
      )
    case 'string':
      return (
        <StringField
          name={name}
          prop={prop}
          value={value}
          error={error}
          onChange={onChange}
        />
      )
    case 'boolean':
      return (
        <BooleanField
          name={name}
          prop={prop}
          value={value}
          error={error}
          onChange={onChange}
        />
      )
    default:
      return (
        <StringField
          name={name}
          prop={prop}
          value={value}
          error={error}
          onChange={onChange}
        />
      )
  }
}

/**
 * Schema-driven parameter form generator.
 *
 * Reads the active schema from effectFormStore and renders appropriate
 * input widgets for each property.
 */
export default function EffectParameterForm() {
  const { schema, parameters, validationErrors, setParameter } =
    useEffectFormStore()

  if (!schema || !schema.properties) {
    return null
  }

  const entries = Object.entries(schema.properties)

  return (
    <div data-testid="effect-parameter-form" className="mt-4">
      <h3 className="mb-3 text-lg font-semibold text-white">Parameters</h3>
      {entries.map(([key, prop]) => (
        <SchemaField
          key={key}
          name={key}
          prop={prop}
          value={parameters[key]}
          error={validationErrors[key]}
          onChange={setParameter}
        />
      ))}
    </div>
  )
}
