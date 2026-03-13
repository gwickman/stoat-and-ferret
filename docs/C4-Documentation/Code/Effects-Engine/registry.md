# Effects Registry

**Source:** `src/stoat_ferret/effects/registry.py`
**Component:** Effects Engine

## Purpose

Provides a registry for discovering and validating available effects with JSON schema validation. Implements the register_handler() pattern from the job queue to provide a consistent interface for effect discovery and parameter validation.

## Public Interface

### Classes

- `EffectRegistry`: Registry of available effects with parameter schemas and AI hints
  - `register(effect_type: str, definition: EffectDefinition) -> None`: Register an effect definition
  - `get(effect_type: str) -> EffectDefinition | None`: Get an effect definition by type
  - `list_all() -> list[tuple[str, EffectDefinition]]`: List all registered effects
  - `validate(effect_type: str, parameters: dict[str, Any]) -> list[EffectValidationError]`: Validate parameters against effect schema

- `EffectValidationError`: Structured validation error from JSON schema validation
  - `__init__(path: str, message: str) -> None`: Initialize with JSON path and error message
  - `path: str`: JSON path to invalid field (e.g., "fontsize")
  - `message: str`: Human-readable error description
  - `__repr__() -> str`: Return string representation

## Dependencies

### Internal Dependencies

- `stoat_ferret.effects.definitions`: Imports `EffectDefinition` class

### External Dependencies

- `jsonschema`: Draft7Validator for JSON schema validation
- `structlog`: Structured logging via `structlog.get_logger(__name__)`

## Key Implementation Details

### Registry Pattern

The `EffectRegistry` class uses a simple dict-based registry pattern:
- Internal storage: `_effects: dict[str, EffectDefinition]`
- Register: Direct dict assignment with logging
- Retrieve: Dict.get() with None fallback
- List: Convert dict items to list of tuples

### Parameter Validation

The `validate()` method:
1. Looks up the effect definition by type (raises KeyError if not found)
2. Creates a `Draft7Validator` instance using the effect's JSON schema
3. Iterates through validation errors from `validator.iter_errors()`
4. Constructs JSON path from `error.absolute_path` (empty string if no path)
5. Returns list of `EffectValidationError` objects (empty if valid)

### Structured Logging

Logging uses structlog:
- `effect_registered`: Logged at INFO level when an effect is registered
- Includes the effect type in log context

### Error Collection

The validation pattern collects all errors rather than failing on the first:
- Uses `iter_errors()` to get iterator of all validation failures
- Constructs human-readable error representation with path and message
- Returns empty list for valid parameters

## Relationships

- **Used by:** Applications creating and querying available effects
- **Uses:** `EffectDefinition` from definitions module and external JSON schema validation
