# Backlog Details - v006

## BL-037: Implement FFmpeg filter expression engine in Rust

- **Priority:** P1 | **Size:** L | **Status:** open
- **Tags:** v006, rust, filters, expressions

**Description:**
> The current filter system (v001) handles simple key=value parameters only. FFmpeg filter expressions like `enable='between(t,3,5)'`, alpha expressions, and time-based arithmetic have no Rust representation. M2.1 requires a type-safe expression builder that prevents syntactically invalid expressions. Without this, text overlay animations (M2.2), speed control (M2.3), and all v007 effects cannot be built safely.

**Acceptance Criteria:**
1. Expression types cover enable, alpha, time, and arithmetic expressions
2. Builder API prevents construction of syntactically invalid expressions at compile time
3. Expressions serialize to valid FFmpeg filter syntax strings
4. Property-based tests (proptest) generate random valid expressions and verify serialization
5. PyO3 bindings expose expression builder to Python with type stubs

**Notes:** None

**Complexity Assessment:** High. Requires designing an expression type system that maps FFmpeg's loosely-typed expression syntax to compile-time-safe Rust types. Proptest integration adds testing complexity. Foundation for BL-040 and BL-041.

---

## BL-038: Implement filter graph validation for pad matching

- **Priority:** P1 | **Size:** L | **Status:** open
- **Tags:** v006, rust, filters, validation

**Description:**
> The current FilterGraph (v001) builds FFmpeg filter strings but performs no validation of input/output pad matching. Invalid graphs (unconnected pads, cycles, mismatched labels) are only caught when FFmpeg rejects the command at runtime. M2.1 requires compile-time-safe graph construction. Without validation, complex filter graphs for effects composition will produce cryptic FFmpeg errors instead of actionable messages.

**Acceptance Criteria:**
1. Pad labels validated for correct matching (output label feeds matching input label)
2. Unconnected pads detected and reported with the specific pad name
3. Graph cycles detected and rejected before serialization
4. Validation error messages include actionable guidance on how to fix the graph
5. Existing FilterGraph tests updated to cover validation

**Notes:** None

**Complexity Assessment:** High. Graph cycle detection requires a topological sort or DFS algorithm. Must integrate with existing FilterGraph without breaking backward compatibility. Foundation for BL-039.

---

## BL-039: Build filter composition system for chaining, branching, and merging

- **Priority:** P1 | **Size:** L | **Status:** open
- **Tags:** v006, rust, filters, composition

**Description:**
> No support exists for composing filter chains programmatically. The current system builds individual filters but cannot chain them sequentially, branch one stream into multiple, or merge multiple streams (e.g., overlay, amix). M2.1 requires a composition API for building complex filter graphs. Without it, every effect combination must manually construct raw filter strings, which is error-prone and unvalidatable.

**Acceptance Criteria:**
1. Chain composition applies filters sequentially to a single stream
2. Branch splits one stream into multiple output streams
3. Merge combines multiple streams using overlay, amix, or concat
4. Composed graphs pass FilterGraph validation automatically
5. PyO3 bindings expose composition API to Python with type stubs

**Notes:** None

**Complexity Assessment:** High. Must support three composition modes (chain, branch, merge) with automatic pad label management. Depends on BL-038 validation. PyO3 bindings add cross-language complexity.

---

## BL-040: Implement drawtext filter builder for text overlays

- **Priority:** P1 | **Size:** L | **Status:** open
- **Tags:** v006, rust, text-overlay

**Description:**
> The `escape_filter_text()` function exists in the Rust sanitize module, but no structured drawtext builder handles position, font, color, shadow, box background, or alpha animation parameters. M2.2 requires a type-safe text overlay system. Without a builder, constructing drawtext filters requires manually assembling complex parameter strings with correct escaping — a frequent source of FFmpeg errors.

**Acceptance Criteria:**
1. Position options support absolute coordinates, centered, and margin-based placement
2. Styling covers font size, color, shadow offset/color, and box background
3. Alpha animation supports fade in/out with configurable duration using expression engine
4. Generated drawtext filters validated as syntactically correct FFmpeg syntax
5. Contract tests verify generated commands pass ffmpeg -filter_complex validation

**Notes:** None

**Complexity Assessment:** High. Many parameter combinations to support. Depends on BL-037 expression engine for alpha animations. Contract tests require FFmpeg binary availability. Builds on existing `escape_filter_text()`.

---

## BL-041: Implement speed control filter builders (setpts/atempo)

- **Priority:** P1 | **Size:** M | **Status:** open
- **Tags:** v006, rust, speed-control

**Description:**
> No Rust types exist for video speed (setpts) or audio speed (atempo) control. M2.3 requires speed adjustment from 0.25x to 4.0x. The atempo filter maxes at 2.0x and requires automatic chaining for higher speeds — a non-obvious FFmpeg detail that should be encapsulated in the builder. Without these builders, speed control must be hand-coded with raw filter strings for each speed value.

**Acceptance Criteria:**
1. Video speed adjustable via setpts with factor range 0.25x–4.0x
2. Audio speed via atempo with automatic chaining for factors above 2.0x
3. Option to drop audio entirely instead of speed-adjusting it
4. Validation rejects out-of-range values with helpful error messages
5. Unit tests cover edge cases: 1x (no-op), boundary values, extreme speeds

**Notes:** None

**Complexity Assessment:** Medium. Narrower scope than other Rust items — two specific FFmpeg filters with well-defined behavior. The atempo chaining logic is the main non-trivial aspect. Depends on BL-037 for expression generation.

---

## BL-042: Create effect discovery API endpoint

- **Priority:** P2 | **Size:** L | **Status:** open
- **Tags:** v006, api, effects, discovery

**Description:**
> M2.2 and 05-api-specification.md specify an `/effects` discovery endpoint, but no such endpoint exists. The frontend needs a way to discover available effects with their parameter schemas and AI hints. Without a discovery endpoint, the GUI must hard-code knowledge of available effects, breaking the extensibility model and preventing the v007 Effect Workshop from dynamically generating parameter forms.

**Acceptance Criteria:**
1. GET /effects returns a list of all available effects
2. Each effect includes name, description, and parameter JSON schema
3. AI hints included for each parameter to guide user input
4. Text overlay and speed control registered as discoverable effects
5. Response includes Rust-generated filter preview for default parameters

**Notes:** None

**Complexity Assessment:** High. Requires designing an effect registration/registry pattern (Python-side). Must define a JSON schema structure for effect parameters that supports the v007 dynamic form generator. Depends on BL-040 and BL-041 being registered.

---

## BL-043: Create API endpoint to apply text overlay effect to clips

- **Priority:** P2 | **Size:** L | **Status:** open
- **Tags:** v006, api, text-overlay

**Description:**
> No API endpoint exists to apply effects to clips. The Rust drawtext builder will generate filter strings, but there is no REST endpoint to receive effect parameters, apply them to a specific clip, and store the configuration in the project model. M2.2 requires this bridge between the Rust effects engine and the clip/project data model. The clip model currently has no field for storing applied effects.

**Acceptance Criteria:**
1. POST endpoint applies text overlay parameters to a specified clip
2. Effect configuration stored persistently in the clip/project model
3. Response includes the generated FFmpeg filter string for transparency
4. Validation errors from Rust surface as structured API error responses
5. Black box test covers the apply -> verify filter string flow

**Notes:** None

**Complexity Assessment:** High. Requires extending the clip data model to store effects — a schema change. Must bridge Python API layer with Rust filter builder. Depends on BL-040 and BL-042. Has a pending investigation dependency (clip effect model design, BL-043 in PLAN.md).
