# v006 Theme Index

## Execution Order

Execute themes in order. Each theme must complete before starting the next.

### Theme 01: filter-engine

**Path:** `comms/inbox/versions/execution/v006/01-filter-engine/`
**Goal:** Build the foundational Rust filter infrastructure — expression type system, filter graph validation, and composition API. These are the building blocks that all downstream filter builders and API endpoints depend on. Corresponds to M2.1 (Filter Expression Engine). Per LRN-019, infrastructure-first sequencing eliminates rework.

**Features:**

- 001-expression-engine: Type-safe Rust expression builder for FFmpeg filter expressions with proptest validation
- 002-graph-validation: Validate FilterGraph pad matching, detect unconnected pads and cycles using Kahn's algorithm
- 003-filter-composition: Programmatic chain, branch, and merge composition with automatic pad label management
### Theme 02: filter-builders

**Path:** `comms/inbox/versions/execution/v006/02-filter-builders/`
**Goal:** Implement concrete filter builders for text overlay and speed control using the expression engine from Theme 01. These are the user-facing effect implementations that the API layer will expose. Corresponds to M2.2 (Text Overlay) and M2.3 (Speed Control).

**Features:**

- 001-drawtext-builder: Type-safe drawtext filter builder with position presets, styling, and alpha animation via expression engine
- 002-speed-builders: setpts and atempo filter builders with automatic atempo chaining for speeds above 2.0x
### Theme 03: effects-api

**Path:** `comms/inbox/versions/execution/v006/03-effects-api/`
**Goal:** Create the Python-side effect registry, discovery API endpoint, clip effect application endpoint, and update architecture documentation. This bridges the Rust filter engine with the REST API and data model. Corresponds to M2.2–M2.3 API integration.

**Features:**

- 001-effect-discovery: Effect registry with parameter schemas, AI hints, and GET /effects endpoint
- 002-clip-effect-api: POST endpoint to apply text overlay to clips with effect storage in clip model
- 003-architecture-docs: Update 02-architecture.md with new Rust modules, Effects Service, and clip model extension
## Notes

- Each feature folder contains requirements.md and implementation-plan.md
- Output documents go to comms/outbox/
- Follow AGENTS.md for implementation process
