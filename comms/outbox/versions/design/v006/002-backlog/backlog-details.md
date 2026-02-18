# Backlog Details - v006

7 backlog items (BL-037 through BL-043) for Effects Engine Foundation.

## BL-037: Implement FFmpeg filter expression engine in Rust

- **Priority:** P1 | **Size:** L | **Tags:** v006, rust, filters, expressions
- **Status:** open

> The current filter system (v001) handles simple key=value parameters only. FFmpeg filter expressions like `enable='between(t,3,5)'`, alpha expressions, and time-based arithmetic have no Rust representation. M2.1 requires a type-safe expression builder that prevents syntactically invalid expressions. Without this, text overlay animations (M2.2), speed control (M2.3), and all v007 effects cannot be built safely.

**Acceptance Criteria:**
1. Expression types cover enable, alpha, time, and arithmetic expressions
2. Builder API prevents construction of syntactically invalid expressions at compile time
3. Expressions serialize to valid FFmpeg filter syntax strings
4. Property-based tests (proptest) generate random valid expressions and verify serialization
5. PyO3 bindings expose expression builder to Python with type stubs

**Complexity:** High. Requires designing a type-safe expression AST that maps to FFmpeg's expression syntax. The compile-time safety constraint and proptest requirement add significant design complexity. This is the foundational item that BL-040, BL-041, and downstream v007 items depend on.

---

## BL-038: Implement filter graph validation for pad matching

- **Priority:** P1 | **Size:** L | **Tags:** v006, rust, filters, validation
- **Status:** open

> The current FilterGraph (v001) builds FFmpeg filter strings but performs no validation of input/output pad matching. Invalid graphs (unconnected pads, cycles, mismatched labels) are only caught when FFmpeg rejects the command at runtime. M2.1 requires compile-time-safe graph construction. Without validation, complex filter graphs for effects composition will produce cryptic FFmpeg errors instead of actionable messages.

**Acceptance Criteria:**
1. Pad labels validated for correct matching (output label feeds matching input label)
2. Unconnected pads detected and reported with the specific pad name
3. Graph cycles detected and rejected before serialization
4. Validation error messages include actionable guidance on how to fix the graph
5. Existing FilterGraph tests updated to cover validation

**Complexity:** High. Graph cycle detection requires topological sort or DFS-based algorithms. Must integrate with the existing FilterGraph without breaking v001 behavior. Pad matching requires modeling FFmpeg's input/output pad semantics accurately.

---

## BL-039: Build filter composition system for chaining, branching, and merging

- **Priority:** P1 | **Size:** L | **Tags:** v006, rust, filters, composition
- **Status:** open

> No support exists for composing filter chains programmatically. The current system builds individual filters but cannot chain them sequentially, branch one stream into multiple, or merge multiple streams (e.g., overlay, amix). M2.1 requires a composition API for building complex filter graphs. Without it, every effect combination must manually construct raw filter strings, which is error-prone and unvalidatable.

**Acceptance Criteria:**
1. Chain composition applies filters sequentially to a single stream
2. Branch splits one stream into multiple output streams
3. Merge combines multiple streams using overlay, amix, or concat
4. Composed graphs pass FilterGraph validation automatically
5. PyO3 bindings expose composition API to Python with type stubs

**Complexity:** High. Depends on BL-038 (validation). Must auto-generate pad labels for composed graphs and ensure they pass validation. The merge operation requires understanding multi-input filter semantics (overlay takes 2 inputs, amix takes N).

---

## BL-040: Implement drawtext filter builder for text overlays

- **Priority:** P1 | **Size:** L | **Tags:** v006, rust, text-overlay
- **Status:** open

> The `escape_filter_text()` function exists in the Rust sanitize module, but no structured drawtext builder handles position, font, color, shadow, box background, or alpha animation parameters. M2.2 requires a type-safe text overlay system. Without a builder, constructing drawtext filters requires manually assembling complex parameter strings with correct escaping -- a frequent source of FFmpeg errors.

**Acceptance Criteria:**
1. Position options support absolute coordinates, centered, and margin-based placement
2. Styling covers font size, color, shadow offset/color, and box background
3. Alpha animation supports fade in/out with configurable duration using expression engine
4. Generated drawtext filters validated as syntactically correct FFmpeg syntax
5. Contract tests verify generated commands pass ffmpeg -filter_complex validation

**Complexity:** High. Depends on BL-037 (expression engine) for alpha animations. FFmpeg drawtext has many parameters with subtle escaping rules. Contract tests require real FFmpeg execution. Must integrate with existing `escape_filter_text()`.

---

## BL-041: Implement speed control filter builders (setpts/atempo)

- **Priority:** P1 | **Size:** M | **Tags:** v006, rust, speed-control
- **Status:** open

> No Rust types exist for video speed (setpts) or audio speed (atempo) control. M2.3 requires speed adjustment from 0.25x to 4.0x. The atempo filter maxes at 2.0x and requires automatic chaining for higher speeds -- a non-obvious FFmpeg detail that should be encapsulated in the builder. Without these builders, speed control must be hand-coded with raw filter strings for each speed value.

**Acceptance Criteria:**
1. Video speed adjustable via setpts with factor range 0.25x-4.0x
2. Audio speed via atempo with automatic chaining for factors above 2.0x
3. Option to drop audio entirely instead of speed-adjusting it
4. Validation rejects out-of-range values with helpful error messages
5. Unit tests cover edge cases: 1x (no-op), boundary values, extreme speeds

**Complexity:** Medium. Depends on BL-037 (expression engine) for setpts expressions. The atempo chaining logic is the main complexity (computing chain of 2.0x filters). Well-bounded scope with clear FFmpeg semantics.

---

## BL-042: Create effect discovery API endpoint

- **Priority:** P2 | **Size:** L | **Tags:** v006, api, effects, discovery
- **Status:** open

> M2.2 and 05-api-specification.md specify an `/effects` discovery endpoint, but no such endpoint exists. The frontend needs a way to discover available effects with their parameter schemas and AI hints. Without a discovery endpoint, the GUI must hard-code knowledge of available effects, breaking the extensibility model and preventing the v007 Effect Workshop from dynamically generating parameter forms.

**Acceptance Criteria:**
1. GET /effects returns a list of all available effects
2. Each effect includes name, description, and parameter JSON schema
3. AI hints included for each parameter to guide user input
4. Text overlay and speed control registered as discoverable effects
5. Response includes Rust-generated filter preview for default parameters

**Complexity:** High. Requires designing an effect registry pattern that can be extended in v007. JSON schema generation for effect parameters. Integration between Python API layer and Rust builders for preview generation. Depends on BL-040 and BL-041 being complete.

---

## BL-043: Create API endpoint to apply text overlay effect to clips

- **Priority:** P2 | **Size:** L | **Tags:** v006, api, text-overlay
- **Status:** open

> No API endpoint exists to apply effects to clips. The Rust drawtext builder will generate filter strings, but there is no REST endpoint to receive effect parameters, apply them to a specific clip, and store the configuration in the project model. M2.2 requires this bridge between the Rust effects engine and the clip/project data model. The clip model currently has no field for storing applied effects.

**Acceptance Criteria:**
1. POST endpoint applies text overlay parameters to a specified clip
2. Effect configuration stored persistently in the clip/project model
3. Response includes the generated FFmpeg filter string for transparency
4. Validation errors from Rust surface as structured API error responses
5. Black box test covers the apply -> verify filter string flow

**Complexity:** High. Requires extending the clip data model to store effects (schema change). Depends on BL-040 and BL-042. May need exploration (BL-043 investigation dependency in PLAN.md) for how effects attach to clips. Bridges Rust engine and Python data model.

---

## Quality Assessment Summary

| ID | Desc Words | Desc Flagged | AC Non-testable | Use Case Formulaic | Action Taken |
|----|-----------|-------------|----------------|-------------------|-------------|
| BL-037 | ~78 | No | 0 | Yes | Rewrote use case |
| BL-038 | ~72 | No | 0 | Yes | Rewrote use case |
| BL-039 | ~68 | No | 0 | Yes | Rewrote use case |
| BL-040 | ~70 | No | 0 | Yes | Rewrote use case |
| BL-041 | ~66 | No | 0 | Yes | Rewrote use case |
| BL-042 | ~74 | No | 0 | Yes | Rewrote use case |
| BL-043 | ~72 | No | 0 | Yes | Rewrote use case |

All 7 items had formulaic use cases (template pattern). All were updated with authentic user scenarios. Descriptions and acceptance criteria were already high quality.
