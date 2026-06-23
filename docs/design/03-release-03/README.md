# Release 3 — Creative Composition, Narration & Accessibility

**Status:** Design phase. Open for refinement. **No backlog items have been filed yet.**
**Builds on:** [Release 2](../02-release-02/README.md) (sound design, mastering, QC-verified delivery).
**Target versions:** v083 onward (six versions: v083-v088).

> **Release 3 is a multi-version release program, not a single auto-dev version.** The proposed implementation map spans v083-v088 (six versions) and should be approved and executed wave-by-wave per `01-roadmap.md`. Do NOT interpret "Release 3" as a single auto-dev version target.

## What Release 3 is

Release 1 made stoat-and-ferret able to *apply effects and render video*. Release 2 made it able to *produce and prove a finished, broadcast-quality master*. Release 3 makes it able to **compose creative multi-clip projects with custom assets, animated effects, narrated audio and accessible subtitles** — closing the gap between "snf can render a single clip" and "snf can produce a finished educational/wellness/marketing piece end-to-end".

Three things define this release:

1. **Render pipeline maturation.** Today the renderer silently drops every clip after the first and every persisted effect. This release rebuilds the render path so the project state the user actually authored becomes the rendered output — multi-clip timelines, per-clip effect chains, timed effect windows, transitions, image-as-clip assets, and a final Windows-compatible pixel format.
2. **Capability expansion driven by two concrete production use cases** — a multi-segment educational explainer and a guided hypnotherapy/wellness session. These exercise multi-clip timelines, animated opacity, image overlays, procedural shapes, voiceover narration (local + cloud), multi-track audio mixing with sidechain ducking, and burned/soft subtitles. Every capability ships with measurable acceptance criteria.
3. **Truth-telling and evidence.** Snf cannot silently succeed any more. A render preflight rejects projects the worker can't represent; render jobs persist an evidence artefact (exact command args, exit code, stderr, output size) the chatbot harness consumes; the verification workflow becomes machine-checkable rather than vibes.

This is built on the same foundations Release 2 established (hybrid Python/Rust, effect-builder registry, QC verification, chatbot/UAT harnesses).

## Design philosophy carried forward

- **Hybrid Python/Rust.** New compute-bound logic (render-graph translation, the bespoke expression parser for BL-514, the geq alpha rewrite for BL-502) lands in Rust pure functions exposed via PyO3. Python orchestrates, validates, serves.
- **Effect-registry pattern.** New effects are builders + JSON-schema-validated registry entries with AI hints, consistent with Releases 1-2. Release 3 extends `EffectDefinition` with the metadata fields the multi-clip render graph needs.
- **Outcome-first requirements.** Every requirement traces to a use case, an outcome (acceptance criterion) and an automated test. Most ACs are machine-verifiable via QC + render-evidence artefacts.
- **Registry authority — Option A locked for Release 3 (per codex `18` Blocker 4):** the existing **Python `EffectDefinition`** at `src/stoat_ferret/effects/definitions.py` **remains authoritative for Release 3**. Python entries point at Rust-backed build functions where compute-bound (BL-505B translator, BL-514 parser, BL-502 geq emit, BL-513 shapes). New metadata fields (`stream_kind`, `arity`, `timeline_T_capable`, etc.) are added to the Python dataclass. A separate v084+ substrate item — "Migrate effect-registry metadata authority to Rust" — owns the eventual move to Rust-authoritative + derived Python hints, including PyO3 binding extension and `_core.pyi` append-only stub updates. **No two-registry split inside Release 3.**

## Document inventory

Read in this order:

| # | File | Description |
|---|------|-------------|
| — | [README.md](README.md) | This overview |
| 1 | [01-roadmap.md](01-roadmap.md) | Scope, capability waves, dependency spine, in/out of scope, version mapping, success gates |
| 2 | [02-architecture.md](02-architecture.md) | New subsystems (multi-input render-graph translator, render evidence artefact, asset library, bespoke parser, TTS provider abstraction) and how they slot into Release 2 architecture |
| 3 | [03-capabilities-and-requirements.md](03-capabilities-and-requirements.md) | Customer-facing capability requirements + non-functional constraints |
| 4 | [04-use-cases.md](04-use-cases.md) | The two production use cases (educational explainer + hypnotherapy session) with detailed flows |
| 5 | [05-api-specification.md](05-api-specification.md) | All new + changed API surfaces |
| 6 | [06-gui-integration.md](06-gui-integration.md) | UI touchpoints for new capabilities |
| 7 | [07-test-strategy.md](07-test-strategy.md) | Contract tests, render-evidence assertions, chatbot-driven verification, UAT scenarios |
| 8 | [08-backlog-items.md](08-backlog-items.md) | The 18 backlog items as a table; full drafts under `backlog/` |
| 9 | [09-traceability-matrix.md](09-traceability-matrix.md) | Use case ↔ requirement ↔ BL ↔ test traceability |
| — | [backlog/](backlog/) | Full backlog item drafts (18 items, not yet filed into MCP) |

## Evidence base

This release is uniquely well-evidenced. Every load-bearing decision is backed by a PoC measurement or a verified third-party fact. The PoC chain that produced this release lives at `<gw-test>/snf-showcase-20260614/gaps-identified/poc-work/` and is summarised in `09-traceability-matrix.md`. PoC artefacts include:

- A working multi-input render-graph translator with SSIM 0.999999 vs source clip attribution
- A 5-variant × 4-filter escape-policy matrix establishing BL-499's path-handling rule
- A geq-with-uppercase-T composition-survival proof for BL-502
- A 9-cell threshold/ratio parameter sweep for BL-517 multi-track ducking
- Live OpenRouter Kokoro TTS synthesis (cloud) + local Piper synthesis (Backend C)
- A 352-line bespoke expression parser spike for BL-514
- An FFmpeg filter-capability table (corrected) covering 25+ filters
- A builder/value-kind audit identifying which existing builders need migration

## Status

These documents represent the **complete design package for Release 3**. Once approved, the backlog drafts under `backlog/` are filed into auto-dev MCP and worked into version plans (v083, v084, ...). The auto-dev process then drives implementation, test-harness updates, documentation updates, and release.

**No backlog items have been filed yet.** That step is gated on user approval of this package.
