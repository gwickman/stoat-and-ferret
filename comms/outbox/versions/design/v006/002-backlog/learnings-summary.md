# Learnings Summary: Applicable to v006

Reviewed 25 learnings (LRN-001 through LRN-025). The following are directly applicable to v006 design.

## Highly Relevant

### LRN-001 — PyO3 Method Chaining with PyRefMut
**Summary:** Use `PyRefMut<'_, Self>` return type for fluent builder APIs that work identically in Rust and Python.
**Applicability:** Directly applies to BL-037 (expression builder), BL-040 (drawtext builder), BL-041 (speed control builder), and BL-039 (composition API). All four need fluent builder APIs exposed to Python.

### LRN-011 — Python Business Logic, Rust Input Safety
**Summary:** Rust handles input sanitization and type safety; Python handles business policy and domain rules.
**Applicability:** Defines the v006 architecture split. BL-037-041 are Rust (expression construction, graph validation, filter building). BL-042-043 are Python (API routing, effect registration, clip model updates).

### LRN-012 — PyO3 FFI Overhead
**Summary:** PyO3 FFI makes Rust 7-10x slower for simple operations. Rust wins only for string-heavy processing.
**Applicability:** v006's Rust builders generate complex FFmpeg filter strings — exactly the string-heavy processing where Rust excels. Justification is correctness (compile-time expression validation) plus string processing performance.

### LRN-019 — Build Infrastructure First
**Summary:** Sequence infrastructure themes before consumer themes.
**Applicability:** BL-037 (expression engine) and BL-038 (graph validation) are infrastructure consumed by BL-039-043. Must be in the first theme.

### LRN-025 — Feature Handoff Documents Enable Zero-Rework Sequencing
**Summary:** Handoff docs communicating integration points enable zero-rework feature chains.
**Applicability:** v006 has a deep dependency chain (BL-037 -> BL-040 -> BL-042 -> BL-043). Handoff documents between features are essential.

## Moderately Relevant

### LRN-003 — Security Validation Whitelist Pattern
**Summary:** Whitelist-based validation for Rust input sanitization.
**Applicability:** The expression engine (BL-037) should validate expression function names against a whitelist of known FFmpeg functions rather than allowing arbitrary strings.

### LRN-005 — Constructor DI over dependency_overrides
**Summary:** Use `create_app()` constructor parameters for test wiring.
**Applicability:** BL-042 and BL-043 add new API endpoints that need DI for effect services. Follow the established `create_app()` kwargs pattern.

### LRN-006 — Builder Pattern with Dual Output Modes for Test Fixtures
**Summary:** Test fixture factories with dual output modes (build/create_via_api).
**Applicability:** v006 should create test fixtures for effect configurations, following the established builder pattern.

### LRN-008 — Record-Replay for External Dependencies
**Summary:** Three-tier executor pattern (Real/Recording/Fake) for FFmpeg testing.
**Applicability:** BL-040 AC5 requires contract tests with `ffmpeg -filter_complex`. The record-replay pattern from v004 applies directly.

### LRN-016 — Validate AC Against Codebase During Design
**Summary:** Check that acceptance criteria reference existing models and APIs.
**Applicability:** BL-043 references "clip/project model" effects storage, but the clip model currently has no effects field. Design must address this gap explicitly.

## Low Relevance (Context Only)

### LRN-002 — Frame-Accurate Timeline Math
**Summary:** Integer-based timeline calculations avoid floating-point drift.
**Applicability:** Speed control (BL-041) involves PTS manipulation. The existing timeline math module may be relevant for frame-accurate speed calculations.

### LRN-007 — Parity Tests Prevent Test Double Drift
**Summary:** Run identical tests against fakes and real implementations.
**Applicability:** If v006 creates InMemory effect repository doubles, parity tests should be included.

### LRN-013 — Progressive Coverage Thresholds
**Summary:** Start conservative, ratchet up coverage thresholds.
**Applicability:** Rust coverage is at 75% (target 90%). New Rust code in v006 should include comprehensive tests to help close this gap.

### LRN-015 — Single-Matrix CI Jobs for Expensive Operations
**Summary:** Run expensive CI on single platform.
**Applicability:** FFmpeg contract tests (BL-040 AC5) should run on a single CI matrix entry, not across all platforms.
