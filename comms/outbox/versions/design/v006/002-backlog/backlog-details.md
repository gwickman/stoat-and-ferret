# Backlog Details: v006

## BL-037 — Implement FFmpeg filter expression engine in Rust (P1, Large)

**Description:**
> The current filter system (v001) handles simple key=value parameters only. FFmpeg filter expressions like `enable='between(t,3,5)'`, alpha expressions, and time-based arithmetic have no Rust representation. M2.1 requires a type-safe expression builder that prevents syntactically invalid expressions. Without this, text overlay animations (M2.2), speed control (M2.3), and all v007 effects cannot be built safely.

**Acceptance Criteria:**
1. Expression types cover enable, alpha, time, and arithmetic expressions
2. Builder API prevents construction of syntactically invalid expressions at compile time
3. Expressions serialize to valid FFmpeg filter syntax strings
4. Property-based tests (proptest) generate random valid expressions and verify serialization
5. PyO3 bindings expose expression builder to Python with type stubs

**Tags:** v006, rust, filters, expressions | **Notes:** None

**Quality Assessment:**
- Description depth: ~80 words, adequate — explains gap, milestone reference, impact
- AC testability: 5/5 have action verbs (cover, prevents, serialize, generate, expose)
- Use case: FORMULAIC — "This feature addresses: {title}..."
- Recommended use case: "A developer building a text overlay effect needs to specify `enable=between(t,3,5)` to show text only during a specific time window. Without a type-safe expression engine, they must manually assemble raw FFmpeg expression strings, risking syntax errors that only surface at FFmpeg execution time."

**Complexity:** High. Requires designing a type-safe AST for FFmpeg expressions, implementing serialization, and creating PyO3 bindings. Property-based testing with proptest adds complexity. This is the foundational piece that BL-040, BL-041, and all v007 effects depend on.

---

## BL-038 — Implement filter graph validation for pad matching (P1, Large)

**Description:**
> The current FilterGraph (v001) builds FFmpeg filter strings but performs no validation of input/output pad matching. Invalid graphs (unconnected pads, cycles, mismatched labels) are only caught when FFmpeg rejects the command at runtime. M2.1 requires compile-time-safe graph construction. Without validation, complex filter graphs for effects composition will produce cryptic FFmpeg errors instead of actionable messages.

**Acceptance Criteria:**
1. Pad labels validated for correct matching (output label feeds matching input label)
2. Unconnected pads detected and reported with the specific pad name
3. Graph cycles detected and rejected before serialization
4. Validation error messages include actionable guidance on how to fix the graph
5. Existing FilterGraph tests updated to cover validation

**Tags:** v006, rust, filters, validation | **Notes:** None

**Quality Assessment:**
- Description depth: ~75 words, adequate — explains current gap, references M2.1
- AC testability: 5/5 have action verbs (validated, detected, detected, include, updated)
- Use case: FORMULAIC
- Recommended use case: "A developer composing a picture-in-picture effect connects an overlay filter's output to the wrong input pad. Without graph validation, the error is only discovered when FFmpeg rejects the command with a cryptic error. Validation catches this at graph construction time with a clear message."

**Complexity:** High. Requires graph theory algorithms (cycle detection via topological sort, connectivity analysis). Must integrate with existing FilterGraph without breaking existing tests. Error messages must be developer-friendly.

---

## BL-039 — Build filter composition system for chaining, branching, and merging (P1, Large)

**Description:**
> No support exists for composing filter chains programmatically. The current system builds individual filters but cannot chain them sequentially, branch one stream into multiple, or merge multiple streams (e.g., overlay, amix). M2.1 requires a composition API for building complex filter graphs. Without it, every effect combination must manually construct raw filter strings, which is error-prone and unvalidatable.

**Acceptance Criteria:**
1. Chain composition applies filters sequentially to a single stream
2. Branch splits one stream into multiple output streams
3. Merge combines multiple streams using overlay, amix, or concat
4. Composed graphs pass FilterGraph validation automatically
5. PyO3 bindings expose composition API to Python with type stubs

**Tags:** v006, rust, filters, composition | **Notes:** None

**Quality Assessment:**
- Description depth: ~70 words, adequate
- AC testability: 5/5 have action verbs (applies, splits, combines, pass, expose)
- Use case: FORMULAIC
- Recommended use case: "A user wants to apply color correction, then add a text overlay, then adjust speed on a single clip. The composition system lets them chain filters sequentially, branch a stream for parallel processing, or merge streams back together — all with automatic pad management and validation."

**Complexity:** High. Depends on BL-038 (validation). Must automatically manage pad labels during composition. Three distinct composition modes (chain, branch, merge) each with different pad semantics.

---

## BL-040 — Implement drawtext filter builder for text overlays (P1, Large)

**Description:**
> The `escape_filter_text()` function exists in the Rust sanitize module, but no structured drawtext builder handles position, font, color, shadow, box background, or alpha animation parameters. M2.2 requires a type-safe text overlay system. Without a builder, constructing drawtext filters requires manually assembling complex parameter strings with correct escaping — a frequent source of FFmpeg errors.

**Acceptance Criteria:**
1. Position options support absolute coordinates, centered, and margin-based placement
2. Styling covers font size, color, shadow offset/color, and box background
3. Alpha animation supports fade in/out with configurable duration using expression engine
4. Generated drawtext filters validated as syntactically correct FFmpeg syntax
5. Contract tests verify generated commands pass ffmpeg -filter_complex validation

**Tags:** v006, rust, text-overlay | **Notes:** None

**Quality Assessment:**
- Description depth: ~70 words, adequate — references existing code, milestone
- AC testability: 5/5 have action verbs (support, covers, supports, validated, verify)
- Use case: FORMULAIC
- Recommended use case: "A content creator wants to add a title card: white text centered on screen, with a semi-transparent black background box, fading in over 0.5 seconds. The drawtext builder lets them specify position, font, color, box styling, and fade animation through a structured API."

**Complexity:** High. Depends on BL-037 (expression engine for alpha animation). FFmpeg's drawtext has many parameters with complex escaping rules. Contract tests require FFmpeg binary availability.

---

## BL-041 — Implement speed control filter builders (setpts/atempo) (P1, Medium)

**Description:**
> No Rust types exist for video speed (setpts) or audio speed (atempo) control. M2.3 requires speed adjustment from 0.25x to 4.0x. The atempo filter maxes at 2.0x and requires automatic chaining for higher speeds — a non-obvious FFmpeg detail that should be encapsulated in the builder. Without these builders, speed control must be hand-coded with raw filter strings for each speed value.

**Acceptance Criteria:**
1. Video speed adjustable via setpts with factor range 0.25x-4.0x
2. Audio speed via atempo with automatic chaining for factors above 2.0x
3. Option to drop audio entirely instead of speed-adjusting it
4. Validation rejects out-of-range values with helpful error messages
5. Unit tests cover edge cases: 1x (no-op), boundary values, extreme speeds

**Tags:** v006, rust, speed-control | **Notes:** None

**Quality Assessment:**
- Description depth: ~70 words, adequate — explains FFmpeg atempo limitation clearly
- AC testability: 5/5 have action verbs (adjustable, via/chaining, option, rejects, cover)
- Use case: FORMULAIC
- Recommended use case: "A video editor wants to create a 3x speed timelapse. They need both video (setpts) and audio (atempo) speed adjustment. FFmpeg's atempo only supports up to 2x, requiring automatic chaining for 3x — the speed control builder handles this automatically."

**Complexity:** Medium. Simpler than BL-037/038/039. The atempo chaining logic is the main complexity. Independent of expression engine (uses simple PTS expressions). Well-bounded scope.

---

## BL-042 — Create effect discovery API endpoint (P2, Large)

**Description:**
> M2.2 and 05-api-specification.md specify an `/effects` discovery endpoint, but no such endpoint exists. The frontend needs a way to discover available effects with their parameter schemas and AI hints. Without a discovery endpoint, the GUI must hard-code knowledge of available effects, breaking the extensibility model and preventing the v007 Effect Workshop from dynamically generating parameter forms.

**Acceptance Criteria:**
1. GET /effects returns a list of all available effects
2. Each effect includes name, description, and parameter JSON schema
3. AI hints included for each parameter to guide user input
4. Text overlay and speed control registered as discoverable effects
5. Response includes Rust-generated filter preview for default parameters

**Tags:** v006, api, effects, discovery | **Notes:** None

**Quality Assessment:**
- Description depth: ~65 words, adequate
- AC testability: 5/5 have action verbs (returns, includes, included, registered, includes)
- Use case: FORMULAIC
- Recommended use case: "The v007 Effect Workshop GUI needs to dynamically render a catalog of available effects with parameter forms. The discovery API returns a machine-readable list of effects with JSON schemas, enabling the GUI to generate parameter forms dynamically and AI tools to suggest appropriate effects."

**Complexity:** High. Requires designing an effect registration pattern, JSON schema generation for parameters, AI hint format. Depends on BL-040 and BL-041 being complete to register effects. Python-side (FastAPI endpoint) but needs to invoke Rust for filter previews.

---

## BL-043 — Create API endpoint to apply text overlay effect to clips (P2, Large)

**Description:**
> No API endpoint exists to apply effects to clips. The Rust drawtext builder will generate filter strings, but there is no REST endpoint to receive effect parameters, apply them to a specific clip, and store the configuration in the project model. M2.2 requires this bridge between the Rust effects engine and the clip/project data model. The clip model currently has no field for storing applied effects.

**Acceptance Criteria:**
1. POST endpoint applies text overlay parameters to a specified clip
2. Effect configuration stored persistently in the clip/project model
3. Response includes the generated FFmpeg filter string for transparency
4. Validation errors from Rust surface as structured API error responses
5. Black box test covers the apply -> verify filter string flow

**Tags:** v006, api, text-overlay | **Notes:** None

**Quality Assessment:**
- Description depth: ~75 words, adequate — identifies clip model gap explicitly
- AC testability: 5/5 have action verbs (applies, stored, includes, surface, covers)
- Use case: FORMULAIC
- Recommended use case: "A user adds a text overlay to clip 3 in their project timeline via the API. The endpoint validates parameters through the Rust drawtext builder, stores the effect configuration on the clip model, and returns the generated FFmpeg filter string for transparency."

**Complexity:** High. Requires extending the clip/project data model with an effects field (schema change). Depends on BL-040 (drawtext builder) and BL-042 (discovery for registration). May need investigation (BL-043 flagged in PLAN.md as possibly needing EXP for clip effect model design).
