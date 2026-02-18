# Project Backlog

*Last updated: 2026-02-18 14:17*

**Total completed:** 32 | **Cancelled:** 0

## Priority Summary

| Priority | Name | Count |
|----------|------|-------|
| P0 | Critical | 0 |
| P1 | High | 16 |
| P2 | Medium | 4 |
| P3 | Low | 1 |

## Quick Reference

| ID | Pri | Size | Title | Description |
|----|-----|------|-------|-------------|
| <a id="bl-019-ref"></a>[BL-019](#bl-019) | P1 | m | Add Windows bash /dev/null guidance to AGENTS.md and nul to .gitignore | Add Windows bash null redirect guidance to AGENTS.md and ... |
| <a id="bl-037-ref"></a>[BL-037](#bl-037) | P1 | l | Implement FFmpeg filter expression engine in Rust | The current filter system (v001) handles simple key=value... |
| <a id="bl-038-ref"></a>[BL-038](#bl-038) | P1 | l | Implement filter graph validation for pad matching | The current FilterGraph (v001) builds FFmpeg filter strin... |
| <a id="bl-039-ref"></a>[BL-039](#bl-039) | P1 | l | Build filter composition system for chaining, branching, and merging | No support exists for composing filter chains programmati... |
| <a id="bl-040-ref"></a>[BL-040](#bl-040) | P1 | l | Implement drawtext filter builder for text overlays | The `escape_filter_text()` function exists in the Rust sa... |
| <a id="bl-041-ref"></a>[BL-041](#bl-041) | P1 | m | Implement speed control filter builders (setpts/atempo) | No Rust types exist for video speed (setpts) or audio spe... |
| <a id="bl-044-ref"></a>[BL-044](#bl-044) | P1 | l | Implement audio mixing filter builders (amix/volume/fade) | No Rust types exist for audio mixing, volume control, or ... |
| <a id="bl-045-ref"></a>[BL-045](#bl-045) | P1 | m | Implement transition filter builders (fade/xfade) | No Rust types exist for video transitions. M2.5 requires ... |
| <a id="bl-046-ref"></a>[BL-046](#bl-046) | P1 | m | Create transition API endpoint for clip-to-clip transitions | M2.5 specifies an `/effects/transition` endpoint for appl... |
| <a id="bl-047-ref"></a>[BL-047](#bl-047) | P1 | l | Build effect registry with JSON schema validation and builder protocol | M2.6 specifies a central effect registry where each effec... |
| <a id="bl-048-ref"></a>[BL-048](#bl-048) | P1 | m | Build effect catalog UI component | M2.8 specifies an effect catalog component for browsing a... |
| <a id="bl-049-ref"></a>[BL-049](#bl-049) | P1 | l | Build dynamic parameter form generator from JSON schema | M2.8 specifies auto-generating parameter forms from JSON ... |
| <a id="bl-050-ref"></a>[BL-050](#bl-050) | P1 | m | Implement live FFmpeg filter preview in effect parameter UI | M2.8 specifies showing the Rust-generated FFmpeg filter s... |
| <a id="bl-051-ref"></a>[BL-051](#bl-051) | P1 | l | Build effect builder workflow with clip selector and effect stack | M2.9 specifies a complete effect builder workflow: select... |
| <a id="bl-053-ref"></a>[BL-053](#bl-053) | P1 | l | Add PR vs BL routing guidance to AGENTS.md (stoat-and-ferret) | AGENTS.md in the stoat-and-ferret project lists both add_... |
| <a id="bl-054-ref"></a>[BL-054](#bl-054) | P1 | l | Add WebFetch safety rules to AGENTS.md | Mirror of auto-dev-mcp BL-517. Add WebFetch safety block ... |
| <a id="bl-018-ref"></a>[BL-018](#bl-018) | P2 | s | Create C4 architecture documentation | No C4 architecture documentation currently exists for the... |
| <a id="bl-042-ref"></a>[BL-042](#bl-042) | P2 | l | Create effect discovery API endpoint | M2.2 and 05-api-specification.md specify an `/effects` di... |
| <a id="bl-043-ref"></a>[BL-043](#bl-043) | P2 | l | Create API endpoint to apply text overlay effect to clips | No API endpoint exists to apply effects to clips. The Rus... |
| <a id="bl-052-ref"></a>[BL-052](#bl-052) | P2 | m | E2E tests for effect workshop workflow | The effect workshop comprises multiple GUI components (ca... |
| <a id="bl-011-ref"></a>[BL-011](#bl-011) | P3 | m | Consolidate Python/Rust build backends | v001 uses hatchling for Python package management and mat... |

## Tags Summary

| Tag | Count | Items |
|-----|-------|-------|
| v007 | 9 | BL-044, BL-045, BL-046, BL-047, ... |
| v006 | 7 | BL-037, BL-038, BL-039, BL-040, ... |
| rust | 7 | BL-037, BL-038, BL-039, BL-040, ... |
| effects | 6 | BL-042, BL-047, BL-048, BL-049, ... |
| gui | 4 | BL-048, BL-049, BL-050, BL-051 |
| agents-md | 3 | BL-019, BL-053, BL-054 |
| filters | 3 | BL-037, BL-038, BL-039 |
| api | 3 | BL-042, BL-043, BL-046 |
| documentation | 2 | BL-018, BL-053 |
| text-overlay | 2 | BL-040, BL-043 |
| transitions | 2 | BL-045, BL-046 |
| tooling | 1 | BL-011 |
| build | 1 | BL-011 |
| complexity | 1 | BL-011 |
| architecture | 1 | BL-018 |
| c4 | 1 | BL-018 |
| windows | 1 | BL-019 |
| gitignore | 1 | BL-019 |
| expressions | 1 | BL-037 |
| validation | 1 | BL-038 |
| composition | 1 | BL-039 |
| speed-control | 1 | BL-041 |
| discovery | 1 | BL-042 |
| audio | 1 | BL-044 |
| mixing | 1 | BL-044 |
| registry | 1 | BL-047 |
| schema | 1 | BL-047 |
| catalog | 1 | BL-048 |
| forms | 1 | BL-049 |
| preview | 1 | BL-050 |
| transparency | 1 | BL-050 |
| builder | 1 | BL-051 |
| testing | 1 | BL-052 |
| e2e | 1 | BL-052 |
| product-requests | 1 | BL-053 |
| decision-framework | 1 | BL-053 |
| webfetch | 1 | BL-054 |
| safety | 1 | BL-054 |
| hang-prevention | 1 | BL-054 |

## Item Details

### P1: High

#### 📋 BL-019: Add Windows bash /dev/null guidance to AGENTS.md and nul to .gitignore

**Status:** open
**Tags:** windows, agents-md, gitignore

Add Windows bash null redirect guidance to AGENTS.md and add `nul` to .gitignore. In bash contexts on Windows: Always use `/dev/null` for output redirection (Git Bash correctly translates this to the Windows null device). Never use bare `nul` which gets interpreted as a literal filename in MSYS/Git Bash environments. Correct: `command > /dev/null 2>&1`. Wrong: `command > nul 2>&1`.

**Use Case:** This feature addresses: Add Windows bash /dev/null guidance to AGENTS.md and nul to .gitignore. It improves the system by resolving the described requirement.

[↑ Back to list](#bl-019-ref)

#### 📋 BL-037: Implement FFmpeg filter expression engine in Rust

**Status:** open
**Tags:** v006, rust, filters, expressions

The current filter system (v001) handles simple key=value parameters only. FFmpeg filter expressions like `enable='between(t,3,5)'`, alpha expressions, and time-based arithmetic have no Rust representation. M2.1 requires a type-safe expression builder that prevents syntactically invalid expressions. Without this, text overlay animations (M2.2), speed control (M2.3), and all v007 effects cannot be built safely.

**Use Case:** This feature addresses: Implement FFmpeg filter expression engine in Rust. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] Expression types cover enable, alpha, time, and arithmetic expressions
- [ ] Builder API prevents construction of syntactically invalid expressions at compile time
- [ ] Expressions serialize to valid FFmpeg filter syntax strings
- [ ] Property-based tests (proptest) generate random valid expressions and verify serialization
- [ ] PyO3 bindings expose expression builder to Python with type stubs

[↑ Back to list](#bl-037-ref)

#### 📋 BL-038: Implement filter graph validation for pad matching

**Status:** open
**Tags:** v006, rust, filters, validation

The current FilterGraph (v001) builds FFmpeg filter strings but performs no validation of input/output pad matching. Invalid graphs (unconnected pads, cycles, mismatched labels) are only caught when FFmpeg rejects the command at runtime. M2.1 requires compile-time-safe graph construction. Without validation, complex filter graphs for effects composition will produce cryptic FFmpeg errors instead of actionable messages.

**Use Case:** This feature addresses: Implement filter graph validation for pad matching. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] Pad labels validated for correct matching (output label feeds matching input label)
- [ ] Unconnected pads detected and reported with the specific pad name
- [ ] Graph cycles detected and rejected before serialization
- [ ] Validation error messages include actionable guidance on how to fix the graph
- [ ] Existing FilterGraph tests updated to cover validation

[↑ Back to list](#bl-038-ref)

#### 📋 BL-039: Build filter composition system for chaining, branching, and merging

**Status:** open
**Tags:** v006, rust, filters, composition

No support exists for composing filter chains programmatically. The current system builds individual filters but cannot chain them sequentially, branch one stream into multiple, or merge multiple streams (e.g., overlay, amix). M2.1 requires a composition API for building complex filter graphs. Without it, every effect combination must manually construct raw filter strings, which is error-prone and unvalidatable.

**Use Case:** This feature addresses: Build filter composition system for chaining, branching, and merging. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] Chain composition applies filters sequentially to a single stream
- [ ] Branch splits one stream into multiple output streams
- [ ] Merge combines multiple streams using overlay, amix, or concat
- [ ] Composed graphs pass FilterGraph validation automatically
- [ ] PyO3 bindings expose composition API to Python with type stubs

[↑ Back to list](#bl-039-ref)

#### 📋 BL-040: Implement drawtext filter builder for text overlays

**Status:** open
**Tags:** v006, rust, text-overlay

The `escape_filter_text()` function exists in the Rust sanitize module, but no structured drawtext builder handles position, font, color, shadow, box background, or alpha animation parameters. M2.2 requires a type-safe text overlay system. Without a builder, constructing drawtext filters requires manually assembling complex parameter strings with correct escaping — a frequent source of FFmpeg errors.

**Use Case:** This feature addresses: Implement drawtext filter builder for text overlays. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] Position options support absolute coordinates, centered, and margin-based placement
- [ ] Styling covers font size, color, shadow offset/color, and box background
- [ ] Alpha animation supports fade in/out with configurable duration using expression engine
- [ ] Generated drawtext filters validated as syntactically correct FFmpeg syntax
- [ ] Contract tests verify generated commands pass ffmpeg -filter_complex validation

[↑ Back to list](#bl-040-ref)

#### 📋 BL-041: Implement speed control filter builders (setpts/atempo)

**Status:** open
**Tags:** v006, rust, speed-control

No Rust types exist for video speed (setpts) or audio speed (atempo) control. M2.3 requires speed adjustment from 0.25x to 4.0x. The atempo filter maxes at 2.0x and requires automatic chaining for higher speeds — a non-obvious FFmpeg detail that should be encapsulated in the builder. Without these builders, speed control must be hand-coded with raw filter strings for each speed value.

**Use Case:** This feature addresses: Implement speed control filter builders (setpts/atempo). It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] Video speed adjustable via setpts with factor range 0.25x–4.0x
- [ ] Audio speed via atempo with automatic chaining for factors above 2.0x
- [ ] Option to drop audio entirely instead of speed-adjusting it
- [ ] Validation rejects out-of-range values with helpful error messages
- [ ] Unit tests cover edge cases: 1x (no-op), boundary values, extreme speeds

[↑ Back to list](#bl-041-ref)

#### 📋 BL-044: Implement audio mixing filter builders (amix/volume/fade)

**Status:** open
**Tags:** v007, rust, audio, mixing

No Rust types exist for audio mixing, volume control, or audio fade effects. M2.4 requires amix for combining audio tracks, per-track volume control, fade in/out, and audio ducking patterns. The existing filter system handles video filters only. Without audio builders, mixing multiple audio sources (music + speech) requires manual FFmpeg filter string construction with no validation or ducking automation.

**Use Case:** This feature addresses: Implement audio mixing filter builders (amix/volume/fade). It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] amix filter builder supports configurable number of input tracks
- [ ] Per-track volume control validates range 0.0–10.0 using existing validate_volume
- [ ] Audio fade in/out supports configurable duration via expression engine
- [ ] Audio ducking pattern lowers music volume during speech segments
- [ ] Edge case tests cover silence, clipping prevention, and format mismatches

[↑ Back to list](#bl-044-ref)

#### 📋 BL-045: Implement transition filter builders (fade/xfade)

**Status:** open
**Tags:** v007, rust, transitions

No Rust types exist for video transitions. M2.5 requires fade in, fade out, crossfade between clips, and xfade with selectable transition effects (wipeleft, slideright, etc.). Transitions are fundamental to video editing but currently have no type-safe builder. Without these, transition effects must be manually assembled as raw FFmpeg filter strings with no parameter validation.

**Use Case:** This feature addresses: Implement transition filter builders (fade/xfade). It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] Fade in/out with configurable duration and color
- [ ] Crossfade between two clips with overlap duration parameter
- [ ] xfade supports selectable effect types (fade, wipeleft, slideright, etc.)
- [ ] Parameter validation rejects invalid duration or effect type with helpful messages
- [ ] PyO3 bindings expose transition builders to Python with type stubs

[↑ Back to list](#bl-045-ref)

#### 📋 BL-046: Create transition API endpoint for clip-to-clip transitions

**Status:** open
**Tags:** v007, api, transitions

M2.5 specifies an `/effects/transition` endpoint for applying transitions between adjacent clips, but no such endpoint exists. The Rust transition builders will generate filter strings, but there is no REST endpoint to receive transition parameters, validate clip adjacency, and store the transition in the project timeline. Without this, transitions cannot be applied through the API.

**Use Case:** This feature addresses: Create transition API endpoint for clip-to-clip transitions. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] POST endpoint applies a transition between two specified clips
- [ ] Validates that the two clips are adjacent in the project timeline
- [ ] Response includes the generated FFmpeg filter string
- [ ] Transition configuration stored persistently in the project model
- [ ] Black box test covers apply transition and verify filter output flow

[↑ Back to list](#bl-046-ref)

#### 📋 BL-047: Build effect registry with JSON schema validation and builder protocol

**Status:** open
**Tags:** v007, registry, effects, schema

M2.6 specifies a central effect registry where each effect is registered with its JSON schema, Rust validation functions, and builder protocol. The v006 discovery endpoint provides basic listing, but the full registry pattern — schema validation, effect builder injection, and metrics tracking — is missing. Without a registry, each effect is independently wired, making the Effect Workshop GUI unable to dynamically generate forms or validate parameters.

**Use Case:** This feature addresses: Build effect registry with JSON schema validation and builder protocol. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] Registry stores effect metadata, parameter JSON schemas, and builder references
- [ ] JSON schema validation enforces parameter constraints for all registered effects
- [ ] Effect builder protocol supports dependency injection for effect construction
- [ ] All existing effects (text overlay, speed, audio, transitions) registered
- [ ] effect_applications_total Prometheus counter increments by effect type on application

[↑ Back to list](#bl-047-ref)

#### 📋 BL-048: Build effect catalog UI component

**Status:** open
**Tags:** v007, gui, effects, catalog

M2.8 specifies an effect catalog component for browsing and selecting available effects, but no such frontend component exists. The `/effects` discovery endpoint (v006) provides the data, but there is no UI to consume it. Users need a visual catalog to discover what effects are available before they can configure and apply them. This is the entry point for the entire Effect Workshop workflow.

**Use Case:** This feature addresses: Build effect catalog UI component. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] Grid/list view displays available effects fetched from /effects endpoint
- [ ] Effect cards show name, description, and category
- [ ] AI hints displayed as contextual tooltips on each effect
- [ ] Search and filter by category narrows the displayed effects
- [ ] Clicking an effect opens its parameter configuration form

[↑ Back to list](#bl-048-ref)

#### 📋 BL-049: Build dynamic parameter form generator from JSON schema

**Status:** open
**Tags:** v007, gui, effects, forms

M2.8 specifies auto-generating parameter forms from JSON schema, but no dynamic form rendering component exists. Each effect has a unique parameter schema (from the effect registry), and building static forms per effect doesn't scale. Without a schema-driven form generator, every new effect requires custom frontend code for its parameter UI, and the live filter preview feature cannot work generically.

**Use Case:** This feature addresses: Build dynamic parameter form generator from JSON schema. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] Forms generated dynamically from effect JSON schema definitions
- [ ] Supports parameter types: number (with range slider), string, enum (dropdown), boolean, color picker
- [ ] Inline validation displays error messages from Rust validation
- [ ] Live filter string preview updates as parameter values change
- [ ] Default values pre-populated from the JSON schema

[↑ Back to list](#bl-049-ref)

#### 📋 BL-050: Implement live FFmpeg filter preview in effect parameter UI

**Status:** open
**Tags:** v007, gui, preview, transparency

M2.8 specifies showing the Rust-generated FFmpeg filter string in real time as users adjust effect parameters. This is the core transparency feature — users see exactly what commands Rust generates. No such preview component exists. Without live preview, the tool's key differentiator (transparency into FFmpeg command generation) is invisible during effect configuration.

**Use Case:** This feature addresses: Implement live FFmpeg filter preview in effect parameter UI. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] Filter string panel displays the current FFmpeg filter and updates on parameter change
- [ ] API calls to get filter preview are debounced to avoid excessive requests
- [ ] FFmpeg filter syntax displayed with syntax highlighting
- [ ] Copy-to-clipboard button copies the filter string for external use

[↑ Back to list](#bl-050-ref)

#### 📋 BL-051: Build effect builder workflow with clip selector and effect stack

**Status:** open
**Tags:** v007, gui, effects, builder

M2.9 specifies a complete effect builder workflow: select effect, configure parameters, choose target clip, view the effect stack per clip, and edit/remove applied effects. No such workflow exists. Individual components (catalog, form, preview) need to be composed into a coherent workflow. Without this, users cannot complete the full loop of discovering, configuring, applying, and managing effects on clips.

**Use Case:** This feature addresses: Build effect builder workflow with clip selector and effect stack. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] Apply to Clip workflow presents a clip selector from the current project
- [ ] Effect stack visualization shows all effects applied to a selected clip in order
- [ ] Preview thumbnail displays a static frame with the effect applied
- [ ] Edit action re-opens parameter form with existing values for an applied effect
- [ ] Remove action deletes an effect from a clip's effect stack with confirmation

[↑ Back to list](#bl-051-ref)

#### 📋 BL-053: Add PR vs BL routing guidance to AGENTS.md (stoat-and-ferret)

**Status:** open
**Tags:** agents-md, product-requests, documentation, decision-framework

AGENTS.md in the stoat-and-ferret project lists both add_product_request and add_backlog_item in the tool inventory but provides no guidance on when to use which. Claude Code sessions following AGENTS.md have no routing guidance for capturing ideas vs filing structured bugs.

The exploration pr-vs-bl-guidance on auto-dev-mcp (Gap 4) identified that AGENTS.md across all managed projects has zero PR vs BL routing guidance. Since AGENTS.md is the first document Claude Code reads in every session, it is the highest-leverage location for this guidance.

Without this, Claude Code defaults to add_backlog_item for all discoveries, bypassing the lightweight product request pathway entirely.

**Use Case:** During any Claude Code session on stoat-and-ferret, the agent reads AGENTS.md first. When it discovers an improvement opportunity mid-implementation, it currently has no guidance on whether to file a PR or BL. With this change, AGENTS.md tells it to default to product requests for ideas and reserve backlog items for structured problems.

**Acceptance Criteria:**
- [ ] AGENTS.md contains a section documenting when to create a Product Request vs a Backlog Item
- [ ] Section includes the maturity gradient: PR for ideas/observations, BL for structured problems with acceptance criteria
- [ ] Section includes the default rule: when in doubt, start with a Product Request
- [ ] Section cross-references add_product_request and add_backlog_item tool_help for detailed guidance

**Notes:** Mirror of BL-510 (auto-dev-mcp). Keep the AGENTS.md addition concise — 3-5 lines max. Content should be identical across all managed projects for consistency.

[↑ Back to list](#bl-053-ref)

#### 📋 BL-054: Add WebFetch safety rules to AGENTS.md

**Status:** open
**Tags:** agents-md, webfetch, safety, hang-prevention

Mirror of auto-dev-mcp BL-517. Add WebFetch safety block to AGENTS.md. Exact text:

## WebFetch Safety (mandatory)
- NEVER WebFetch a URL you generated from memory — only WebFetch URLs returned by WebSearch
- Prefer WebSearch over WebFetch for research
- MANDATORY: Before every WebFetch call you MUST run: curl -sL --max-time 10 -o /dev/null -w "%{http_code}" &lt;url&gt; and ONLY proceed with WebFetch if curl returns 2xx/3xx

stoat-and-ferret v006 Task 004 was the first incident — 2 hung WebFetch calls froze the session for 3 hours.

**Use Case:** Same as BL-517: prevent WebFetch hangs from freezing sessions by requiring URL verification before every WebFetch call.

**Acceptance Criteria:**
- [ ] AGENTS.md contains a '## WebFetch Safety (mandatory)' section with all 3 rules verbatim
- [ ] The section is placed near top-level instructions, not buried at the end
- [ ] No other changes to AGENTS.md beyond the insertion

[↑ Back to list](#bl-054-ref)

### P2: Medium

#### 📋 BL-018: Create C4 architecture documentation

**Status:** open
**Tags:** documentation, architecture, c4

No C4 architecture documentation currently exists for the project. Establish documentation at appropriate levels (Context, Container, Component, Code) to document the system architecture.

**Use Case:** This feature addresses: Create C4 architecture documentation. It improves the system by resolving the described requirement.

**Notes:** v004 retrospective architecture check (2026-02-09): The primary architecture doc (docs/design/02-architecture.md) was updated during v004 Theme 03 Feature 3 to reflect async scan, job queue, and updated data flows. No additional drift detected in the design docs. However, the v004 version retrospective explicitly notes that C4 documentation was skipped. v004 added: (1) AsyncioJobQueue with handler registration and background worker, (2) GET /api/v1/jobs/{job_id} status endpoint, (3) ALLOWED_SCAN_ROOTS security configuration with validate_scan_path(), (4) InMemory test doubles and create_app() DI pattern, (5) Docker multi-stage build infrastructure, (6) Rust coverage CI enforcement. These components should be captured when C4 documentation is created.

v005 retrospective architecture check (2026-02-09): The design doc (docs/design/02-architecture.md) already includes /ws and /gui endpoint groups and high-level WebSocket/frontend descriptions added during v004. No C4 documentation exists (docs/C4-Documentation/ not found). v005 added significant frontend architecture not yet documented at the component level: (1) React/TypeScript/Vite frontend with Tailwind CSS v4, (2) ConnectionManager for WebSocket with lazy dead-connection cleanup, (3) ThumbnailService with GET /api/v1/videos/{id}/thumbnail endpoint, (4) AsyncVideoRepository.count() protocol method, (5) GUI components: Shell layout, Dashboard panel, Library Browser, Project Manager, (6) Zustand state management with 3 stores (activityStore, libraryStore, projectStore), (7) Playwright E2E testing infrastructure with CI job, (8) New settings: thumbnail_dir, gui_static_path, ws_heartbeat_interval. The design doc captures the high-level architecture correctly but lacks frontend component-level detail. C4 documentation would address this gap comprehensively.

[↑ Back to list](#bl-018-ref)

#### 📋 BL-042: Create effect discovery API endpoint

**Status:** open
**Tags:** v006, api, effects, discovery

M2.2 and 05-api-specification.md specify an `/effects` discovery endpoint, but no such endpoint exists. The frontend needs a way to discover available effects with their parameter schemas and AI hints. Without a discovery endpoint, the GUI must hard-code knowledge of available effects, breaking the extensibility model and preventing the v007 Effect Workshop from dynamically generating parameter forms.

**Use Case:** This feature addresses: Create effect discovery API endpoint. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] GET /effects returns a list of all available effects
- [ ] Each effect includes name, description, and parameter JSON schema
- [ ] AI hints included for each parameter to guide user input
- [ ] Text overlay and speed control registered as discoverable effects
- [ ] Response includes Rust-generated filter preview for default parameters

[↑ Back to list](#bl-042-ref)

#### 📋 BL-043: Create API endpoint to apply text overlay effect to clips

**Status:** open
**Tags:** v006, api, text-overlay

No API endpoint exists to apply effects to clips. The Rust drawtext builder will generate filter strings, but there is no REST endpoint to receive effect parameters, apply them to a specific clip, and store the configuration in the project model. M2.2 requires this bridge between the Rust effects engine and the clip/project data model. The clip model currently has no field for storing applied effects.

**Use Case:** This feature addresses: Create API endpoint to apply text overlay effect to clips. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] POST endpoint applies text overlay parameters to a specified clip
- [ ] Effect configuration stored persistently in the clip/project model
- [ ] Response includes the generated FFmpeg filter string for transparency
- [ ] Validation errors from Rust surface as structured API error responses
- [ ] Black box test covers the apply → verify filter string flow

[↑ Back to list](#bl-043-ref)

#### 📋 BL-052: E2E tests for effect workshop workflow

**Status:** open
**Tags:** v007, testing, e2e, effects

The effect workshop comprises multiple GUI components (catalog, form generator, preview, builder workflow) that must work together end-to-end. No E2E tests cover this workflow. The v005 Playwright infrastructure provides the foundation, but effect-specific test scenarios are needed. Without E2E coverage, regressions in the multi-step effect application workflow go undetected.

**Use Case:** This feature addresses: E2E tests for effect workshop workflow. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] E2E test browses effect catalog and selects an effect
- [ ] E2E test configures parameters and verifies filter preview updates in real time
- [ ] E2E test applies effect to a clip and verifies effect stack display
- [ ] E2E test edits and removes an applied effect successfully
- [ ] Accessibility checks (WCAG AA) pass for all form components

[↑ Back to list](#bl-052-ref)

### P3: Low

#### 📋 BL-011: Consolidate Python/Rust build backends

**Status:** open
**Tags:** tooling, build, complexity

v001 uses hatchling for Python package management and maturin for Rust/PyO3 builds. This dual-backend approach adds complexity. Evaluate whether the build system can be simplified.

**Use Case:** This feature addresses: Consolidate Python/Rust build backends. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] Evaluate if hatchling + maturin can be unified
- [ ] Document build system architecture and rationale
- [ ] Simplify if possible without breaking functionality
- [ ] Update developer documentation

[↑ Back to list](#bl-011-ref)
