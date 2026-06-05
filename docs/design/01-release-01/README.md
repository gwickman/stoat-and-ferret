# Release 1 — Design Corpus (as-built)

This folder contains the **Release 1** design documentation: everything stoat-and-ferret designed and built across its initial development arc (Phases 1–6, versions ~v001–v072). It is the as-built record of the hybrid Python/Rust AI-driven video editor: library management, timeline/clip model, effects engine, composition, preview/proxy, render pipeline, GUI, and deployment.

Release 1 is **closed**. New capability design lives in [`../02-release-02/`](../02-release-02/README.md).

## Contents

### Top-level design set (product + architecture)

| Document | Description |
|----------|-------------|
| [01-roadmap.md](01-roadmap.md) | Phased implementation roadmap (Phases 1–6) |
| [02-architecture.md](02-architecture.md) | Detailed system architecture, data models, flows |
| [03-prototype-design.md](03-prototype-design.md) | MVP scope and prototype design |
| [04-technical-stack.md](04-technical-stack.md) | Technology stack and dependencies |
| [05-api-specification.md](05-api-specification.md) | REST API specification |
| [05-gui-integration.md](05-gui-integration.md) | GUI integration spec |
| [06-risk-assessment.md](06-risk-assessment.md) | Risk register and mitigations |
| [07-quality-architecture.md](07-quality-architecture.md) | Quality attributes, testing patterns, black-box harness |
| [08-gui-architecture.md](08-gui-architecture.md) | GUI architecture and AI Theater Mode |
| [09-security-audit.md](09-security-audit.md) | Security review |
| [10-performance-benchmarks.md](10-performance-benchmarks.md) | Performance benchmarks |
| [security-review-drawtext.md](security-review-drawtext.md) | Focused security review of drawtext input handling |

### Per-phase design folders

- `Phase 03 Design/` — Composition engine (PIP, split-screen, multi-track, layers)
- `Phase 04 Design/` — Preview & playback (proxy, HLS, waveforms, Theater Mode)
- `Phase 05 Design/` — Export & production (render coordinator, encoders, job queue)
- `Phase 06 Design/` — Deployability & AI integration

## Cross-cutting docs (kept at `docs/design/` root)

These span releases and are **not** part of the Release 1 lock:

- `FRAMEWORK_CONTEXT.md`, `VALIDATION_FRAMEWORK.md` — framework context and validation rules
- `chatbot-driven-testing/` — chatbot-driven testing harness design
- `uat_test/` — UAT (browser) harness design
- `sample_project/` — seeded sample-project fixture
- `smoke_test/` — smoke-test harness

> Note: the testing harnesses above are promoted to **first-class citizens** in Release 2. See [`../02-release-02/07-test-strategy.md`](../02-release-02/07-test-strategy.md).
