# Learnings Summary — Relevant to v004

Three project learnings exist in `docs/auto-dev/LEARNINGS/`, all from the v001 retrospective.

## LRN-001: PyO3 Method Chaining with PyRefMut

**Relevance to v004**: Medium — applies to BL-022 (fixture factory builder pattern)

The builder pattern using `PyRefMut<'_, Self>` for method chaining works identically in Rust and Python. This is relevant if the fixture factory (BL-022) includes any Rust-side builder types, though the primary builder will likely be Python-only. More directly relevant if v004 adds new Rust types with builder APIs.

**Key pattern**: Return `PyRefMut<'_, Self>` for fluent chaining without cloning.

## LRN-002: Frame-Accurate Timeline Math

**Relevance to v004**: Low-Medium — applies to BL-026 (benchmarks)

Integer frame counts with rational frame rates eliminate floating-point accumulation errors. For benchmarking (BL-026), this is one of the representative operations to measure — timeline position calculations in Rust vs Python should show significant speedup since Rust integer arithmetic avoids Python object overhead.

**Key pattern**: u64 frame counts internally, f64 only at API boundaries.

## LRN-003: Security Validation Whitelist Pattern

**Relevance to v004**: High — directly applies to BL-025 (security audit)

The whitelist-over-blacklist principle is the primary pattern to verify during the security audit. The audit should confirm that:
- Codec validation uses whitelists (already implemented)
- File path extensions use whitelists
- Filter names use whitelists
- Any new user-provided values added since v001 follow the whitelist pattern

**Key pattern**: Reject unknown values by default; explicitly enumerate allowed values.

## Gaps in Learnings

No learnings exist related to:
- **Testing patterns** — No documented learnings about test double strategies, fixture patterns, or integration test approaches. v004's heavy testing focus may generate new learnings.
- **CI/CD patterns** — No learnings about CI configuration, coverage tooling, or Docker environments.
- **Async patterns** — No learnings about async job queues or background task management.

These gaps suggest v004 should document new learnings as testing infrastructure is built out.
