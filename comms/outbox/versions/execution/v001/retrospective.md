# v001 Version Retrospective

## Version Summary

**Version:** v001
**Title:** Foundation Version - Hybrid Python/Rust Architecture
**Status:** Complete
**Started:** 2026-01-26
**Completed:** 2026-01-26

Version v001 established the foundational architecture for the stoat-and-ferret video editor project. This version delivered:

- **Project Foundation**: Modern Python tooling (uv, ruff, mypy, pytest) with Rust workspace and PyO3 bindings, plus cross-platform CI pipeline
- **Timeline Math**: Frame-accurate position calculations, clip validation, and range arithmetic in Rust
- **Command Builder**: Type-safe FFmpeg command construction with filter chains, input sanitization, and full Python bindings

All 10 features across 3 themes completed successfully with all acceptance criteria met and quality gates passing on Ubuntu, Windows, and macOS with Python 3.10, 3.11, and 3.12.

## Theme Results

| Theme | Features | Status | Acceptance Criteria | Notes |
|-------|----------|--------|---------------------|-------|
| 01-project-foundation | 3/3 | Complete | 15/15 | Python tooling, Rust workspace, CI pipeline |
| 02-timeline-math | 3/3 | Complete | 11/11 | Position calculations, clip validation, range arithmetic |
| 03-command-builder | 4/4 | Complete | 16/16 | Command construction, filter chain, sanitization, PyO3 bindings |

**Total:** 10/10 features, 42/42 acceptance criteria (100%)

## C4 Documentation

**Status:** Not attempted (skipped)

C4 architecture documentation regeneration was not performed for this version. This should be considered for v002 if the codebase has stabilized enough to warrant formal architecture documentation.

## Cross-Theme Learnings

### Patterns That Emerged Across Themes

1. **Incremental Layering Works Well**
   - Theme 01 built Python tooling first, then Rust, then CI
   - Theme 02 built position types, then validation, then range operations
   - Theme 03 built commands, then filters, then sanitization, then bindings
   - Each feature built on the previous, reducing integration risk

2. **PyO3 Method Chaining Pattern**
   - Using `PyRefMut<'_, Self>` enables fluent APIs that work identically in Rust and Python
   - This pattern was established in Theme 02 and refined in Theme 03
   - Example: `FFmpegCommand().input("a.mp4").output("b.mp4").build()` works in both languages

3. **Frame-Accurate Integer Representation**
   - Using `u64` frame counts internally eliminates floating-point precision drift
   - Rational frame rates (numerator/denominator) allow exact NTSC/PAL representation
   - f64 conversion only at API boundaries

4. **Result-Returning Construction**
   - Type constructors that can fail return `Result<T, E>` to enforce valid state invariants
   - ValidationError includes field, message, actual, and expected for actionable errors
   - Rust validation automatically available to Python through PyO3

5. **Quality Gate Stack**
   - Python: ruff check + format, mypy strict mode, pytest with 80% coverage threshold
   - Rust: cargo fmt, clippy -D warnings, cargo test
   - CI validates on 3 platforms × 3 Python versions

### Anti-Patterns Avoided

1. **Deferred Python Bindings**: Theme 02 noted "PyO3 bindings not yet added" for clip/range modules; Theme 03 explicitly added bindings as a dedicated feature rather than deferring further.

2. **Manual Stub Drift**: Recognized early that manual type stubs could drift from Rust implementation; consistently maintained stubs alongside Rust changes.

## Technical Debt Summary

### High Priority (Address in v002)

| Item | Source | Severity | Description |
|------|--------|----------|-------------|
| Incomplete Python Bindings | Theme 02 | Medium | Clip and ValidationError types not yet exposed to Python |
| TimeRange Python Bindings | Theme 02 | Medium | TimeRange and list operations not yet exposed to Python |

### Low Priority (Track for Future)

| Item | Source | Severity | Description |
|------|--------|----------|-------------|
| Manual Type Stubs | Themes 01-03 | Low | Stubs manually maintained; pyo3-stub-gen in place but not automated |
| No Rust Coverage | Themes 01-02 | Low | llvm-cov not configured; Rust code coverage not tracked |
| Stub Verification | Theme 01 | Low | CI only verifies stubs exist, not that they match Rust API |
| Build Backend Duality | Theme 01 | Low | Using hatchling for Python with maturin for Rust builds |
| RangeError Not Exposed | Theme 02 | Low | Error type defined but not used in public API |
| Test API Naming | Theme 03 | Low | Some Python methods have `py_` prefixes or different names |
| Coverage Reporting Gaps | Theme 03 | Low | ImportError fallback excluded from coverage |

## Process Improvements

### For AGENTS.md

1. **Add PyO3 Bindings Incrementally**: When implementing new Rust types, add Python bindings and type stubs in the same feature rather than deferring to a later feature.

2. **Property Tests as Specification**: Consider writing proptest invariants before implementation as executable specifications.

3. **Test Count Tracking**: The progression from 37 → 61 → 111 → 200+ Rust tests shows healthy growth. Document expected test counts in feature plans.

### For Process Docs

1. **Cross-Platform Testing Pattern**: The 3×3 matrix (OS × Python version) caught platform-specific issues. Document this as the standard CI configuration.

2. **Validation Whitelist Pattern**: Prefer whitelisting known-good values over blacklisting dangerous ones for security-sensitive inputs.

3. **Builder Pattern for PyO3**: Document the `PyRefMut<'_, Self>` pattern for fluent method chaining in cross-language APIs.

## Statistics

| Metric | Value |
|--------|-------|
| **Themes Completed** | 3/3 (100%) |
| **Features Completed** | 10/10 (100%) |
| **Acceptance Criteria Met** | 42/42 (100%) |
| **Rust Tests** | 200+ unit + 83 doc tests |
| **Python Tests** | ~50 integration tests |
| **Python Test Coverage** | 86% |
| **Platforms Supported** | 3 (Ubuntu, Windows, macOS) |
| **Python Versions Supported** | 3 (3.10, 3.11, 3.12) |
| **New Rust Modules** | position, clip, range, command, filter, sanitize |
| **New Python Modules** | stoat_ferret_core |
| **Type Stub Files** | 2 |

## Version Artifacts

- Theme 01 Retrospective: `comms/outbox/versions/execution/v001/01-project-foundation/retrospective.md`
- Theme 02 Retrospective: `comms/outbox/versions/execution/v001/02-timeline-math/retrospective.md`
- Theme 03 Retrospective: `comms/outbox/versions/execution/v001/03-command-builder/retrospective.md`
- Status File: `comms/outbox/versions/execution/v001/STATUS.md`
