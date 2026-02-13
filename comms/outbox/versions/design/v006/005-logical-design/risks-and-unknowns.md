# Risks and Unknowns: v006 — Effects Engine Foundation

## Risk: Clip effects storage model design is unresolved

- **Severity**: high
- **Description**: BL-043 requires storing effect configurations on clips, but the current clip model (Pydantic schema, DB repository, Rust `Clip` type) has no `effects` field. This is a multi-layer schema change touching Python, DB, and potentially Rust. The impact assessment (impact #9) flagged this as substantial. The clip effect model design was identified as potentially needing a dedicated exploration (EXP BL-043, status: pending).
- **Investigation needed**: Define the effect configuration storage format — JSON blob vs typed schema, effects as a list vs map, whether Rust `Clip` type needs the field or only Python-side. Determine if DB migration is needed for persisted clip data.
- **Current assumption**: Effects stored as a JSON list on the clip Pydantic model and serialized to DB. Rust `Clip` type does not need the field (Python handles effect storage, Rust handles filter generation). Feature 002 in Theme 03 is dedicated to this design work.

## Risk: Effect registry pattern needs upfront design for extensibility

- **Severity**: high
- **Description**: BL-042's effect registry service must be extensible for v007 effects (Effect Workshop). The impact assessment (impact #13) flagged this as substantial. The registry pattern (how effects self-register, how parameter schemas are generated, how AI hints are structured) has no precedent in the codebase. Poor design here creates tech debt that compounds in v007.
- **Investigation needed**: Define the effect registration interface — decorator-based vs explicit registration, schema generation approach (manual vs auto from Pydantic models), AI hint format specification. Review how the DI pattern (`create_app()` kwargs) should surface the registry.
- **Current assumption**: Explicit registration via a Python `EffectRegistry` service injected via `create_app()` kwargs. Each effect provides a registration object with name, description, parameter Pydantic model (auto-schema via JSON Schema), and AI hints dict.

## Risk: Task 004 research was incomplete

- **Severity**: medium
- **Description**: The research investigation (Task 004) timed out without producing substantive findings. Key research questions remain unresolved: FFmpeg filter expression syntax subset, graph validation rules, drawtext parameter priority, speed control approach details, and BL-043 clip model design.
- **Investigation needed**: Implementation workers should consult FFmpeg documentation during feature implementation. The existing v001 command builder and filter module in the Rust crate provide the primary code reference for patterns.
- **Current assumption**: Research gaps are addressable during implementation because v006 is greenfield Rust work. The existing codebase patterns (command builder, filter types) and FFmpeg documentation are sufficient references. No blocking research questions prevent design from proceeding.

## Risk: FFmpeg filter expression subset scope creep

- **Severity**: medium
- **Description**: FFmpeg's expression language is extensive (time functions, conditional expressions, random, print, etc.). BL-037's AC specifies "enable, alpha, time, and arithmetic expressions" but the full scope of functions to whitelist is unclear. Over-scoping the expression engine delays Theme 01; under-scoping blocks downstream features.
- **Investigation needed**: Enumerate the specific FFmpeg expression functions needed by BL-040 (drawtext: `between`, `if`, alpha expressions) and BL-041 (speed: PTS expressions). Build the whitelist from actual downstream requirements, not the full FFmpeg expression specification.
- **Current assumption**: Start with the minimal function set needed by drawtext and speed control builders. Expression engine should be extensible (add new functions without breaking existing API) but v006 only implements what v006 consumers need.

## Risk: Rust coverage threshold gap

- **Severity**: medium
- **Description**: Rust coverage is at ~75% against a 90% target (deferred from v004). v006 adds significant new Rust code (expression engine, graph validation, composition, drawtext, speed control). If new code has lower-than-90% coverage, the gap widens further.
- **Investigation needed**: Track Rust coverage during implementation. Ensure proptest and unit tests are comprehensive for all new modules.
- **Current assumption**: The extensive unit test requirements in the test strategy (proptest for BL-037, edge case coverage for BL-041, contract tests for BL-040) should bring new module coverage above 90%. Whether this raises the overall crate coverage to 90% depends on existing code gaps.

## Risk: BL-043 depends on two substantial impacts being resolved

- **Severity**: medium
- **Description**: BL-043 (text overlay clip API) depends on both the clip effects model (impact #9) and the effect registry (impact #13). These are the only two substantial impacts in v006. If either takes longer than expected, BL-043 is blocked.
- **Investigation needed**: Feature 001 (discovery/registry) and Feature 002 (clip model) in Theme 03 are sequenced before Feature 003 (apply endpoint) specifically to resolve these dependencies. Monitor their progress.
- **Current assumption**: Splitting BL-043 into two features (model + endpoint) and sequencing discovery first provides sufficient structure. The `create_app()` DI pattern is well-established and should accelerate registry integration.

## Risk: Contract tests require FFmpeg binary in CI

- **Severity**: low
- **Description**: BL-040 AC5 requires contract tests that run `ffmpeg -filter_complex` validation. CI must have FFmpeg available. The existing CI infrastructure has FFmpeg for record-replay tests (v004), but filter-level contract tests may need different invocation.
- **Investigation needed**: Verify CI workflow installs FFmpeg and that filter-complex validation works in CI environment. Check if existing contract test infrastructure extends cleanly to filter-level validation.
- **Current assumption**: Existing CI FFmpeg setup from v004 is sufficient. Contract tests run on single CI matrix entry per LRN-015. Record-replay pattern (LRN-008) provides the test infrastructure pattern.

## Risk: Drop-frame timecode may intersect with speed control

- **Severity**: low
- **Description**: Drop-frame timecode support was deferred from v001. Speed control (BL-041) involves PTS manipulation. If drop-frame timecode affects PTS calculations for NTSC-rate content, speed control may produce incorrect results for some frame rates.
- **Investigation needed**: Determine if BL-041's setpts approach is frame-rate-independent (operates on PTS values, not timecodes). If so, drop-frame is irrelevant.
- **Current assumption**: Speed control operates on PTS values via `PTS/factor`, which is frame-rate-independent. Drop-frame timecode is a display/timecode concern, not a PTS calculation concern. No intersection expected.
