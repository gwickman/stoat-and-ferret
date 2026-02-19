# Project Backlog

*Last updated: 2026-02-19 07:09*

**Total completed:** 40 | **Cancelled:** 0

## Priority Summary

| Priority | Name | Count |
|----------|------|-------|
| P0 | Critical | 0 |
| P1 | High | 11 |
| P2 | Medium | 1 |
| P3 | Low | 1 |

## Quick Reference

| ID | Pri | Size | Title | Description |
|----|-----|------|-------|-------------|
| <a id="bl-019-ref"></a>[BL-019](#bl-019) | P1 | m | Add Windows bash /dev/null guidance to AGENTS.md and nul to .gitignore | Add Windows bash null redirect guidance to AGENTS.md and ... |
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
| <a id="bl-052-ref"></a>[BL-052](#bl-052) | P2 | m | E2E tests for effect workshop workflow | The effect workshop comprises multiple GUI components (ca... |
| <a id="bl-011-ref"></a>[BL-011](#bl-011) | P3 | m | Consolidate Python/Rust build backends | v001 uses hatchling for Python package management and mat... |

## Tags Summary

| Tag | Count | Items |
|-----|-------|-------|
| v007 | 9 | BL-044, BL-045, BL-046, BL-047, ... |
| effects | 5 | BL-047, BL-048, BL-049, BL-051, ... |
| gui | 4 | BL-048, BL-049, BL-050, BL-051 |
| agents-md | 3 | BL-019, BL-053, BL-054 |
| rust | 2 | BL-044, BL-045 |
| transitions | 2 | BL-045, BL-046 |
| tooling | 1 | BL-011 |
| build | 1 | BL-011 |
| complexity | 1 | BL-011 |
| windows | 1 | BL-019 |
| gitignore | 1 | BL-019 |
| audio | 1 | BL-044 |
| mixing | 1 | BL-044 |
| api | 1 | BL-046 |
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
| documentation | 1 | BL-053 |
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
