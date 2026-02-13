# Theme Index: v006

## Theme 01: filter-expression-infrastructure

Build the foundational Rust infrastructure — a type-safe expression engine for FFmpeg filter expressions and a graph validation system for verifying filter graph correctness before serialization.

**Features:**

- 001-expression-engine: Implement type-safe FFmpeg expression AST with builder API, serialization, property-based tests, and PyO3 bindings
- 002-graph-validation: Add pad matching validation, unconnected pad detection, and cycle detection to FilterGraph with actionable error messages

## Theme 02: filter-builders-and-composition

Build the concrete filter builders (drawtext, speed control) and the composition system for chaining, branching, and merging filter graphs.

**Features:**

- 001-filter-composition: Build chain/branch/merge composition API with automatic pad management and validation
- 002-drawtext-builder: Implement drawtext filter builder with position, styling, alpha animation, and contract tests
- 003-speed-control: Implement setpts/atempo builders with automatic atempo chaining for speeds above 2x

## Theme 03: effects-api-layer

Bridge the Rust effects engine to the Python API layer with discovery and application endpoints.

**Features:**

- 001-effect-discovery: Create GET /effects endpoint with registry service, parameter JSON schemas, and AI hints
- 002-clip-effect-model: Extend clip data model with effects storage across Python schema, DB repository, and Alembic migration
- 003-text-overlay-apply: Create POST endpoint to apply text overlay to clips with validation, persistence, and filter preview
