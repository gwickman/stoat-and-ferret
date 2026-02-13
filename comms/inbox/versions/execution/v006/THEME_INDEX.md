# v006 Theme Index

## Execution Order

Execute themes in order. Each theme must complete before starting the next.

### Theme 01: filter-expression-infrastructure

**Path:** `comms/inbox/versions/execution/v006/01-filter-expression-infrastructure/`
**Goal:** Build the foundational Rust infrastructure that all other v006 features depend on — a type-safe expression engine for FFmpeg filter expressions and a graph validation system for verifying filter graph correctness before serialization. These two independent subsystems form the base layer of the effects engine and can execute in parallel.

**Features:**

- 001-expression-engine: _Feature description_
- 002-graph-validation: _Feature description_
### Theme 02: filter-builders-and-composition

**Path:** `comms/inbox/versions/execution/v006/02-filter-builders-and-composition/`
**Goal:** Build the concrete filter builders (drawtext for text overlays, speed control for setpts/atempo) and the composition system for chaining, branching, and merging filter graphs. These features consume Theme 01's infrastructure and produce the Rust-side building blocks that the API layer (Theme 03) needs.

**Features:**

- 001-filter-composition: _Feature description_
- 002-drawtext-builder: _Feature description_
- 003-speed-control: _Feature description_
### Theme 03: effects-api-layer

**Path:** `comms/inbox/versions/execution/v006/03-effects-api-layer/`
**Goal:** Bridge the Rust effects engine to the Python API layer. Create the effect discovery endpoint with a registry pattern and parameter schemas, extend the clip data model for effect storage, and implement the text overlay application endpoint. This theme transitions from Rust-side construction to Python-side orchestration.

**Features:**

- 001-effect-discovery: _Feature description_
- 002-clip-effect-model: _Feature description_
- 003-text-overlay-apply: _Feature description_
## Notes

- Each feature folder contains requirements.md and implementation-plan.md
- Output documents go to comms/outbox/
- Follow AGENTS.md for implementation process
