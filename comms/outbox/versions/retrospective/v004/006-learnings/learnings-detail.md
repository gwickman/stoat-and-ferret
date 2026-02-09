# v004 Learnings Detail

Full content for each learning saved during the v004 learnings extraction.

---

## LRN-004: Deepcopy Isolation for InMemory Test Doubles

**Tags:** testing, patterns, isolation, test-doubles
**Source:** v004/01-test-foundation/001-inmemory-test-doubles

### Context

When building in-memory repository implementations for testing, mutation isolation between test cases is critical. If test doubles share object references with callers, one test's modifications can leak into another.

### Learning

Apply `deepcopy()` on **both read and write operations** in InMemory repository implementations. Deepcopy only on read still allows callers to mutate stored state via input references from write operations. Both directions must be isolated.

### Evidence

- v004 Theme 01 Feature 001 (inmemory-test-doubles): All three InMemory repositories (Project, Video, Clip) required deepcopy on both `add()`/`update()` inputs and `get()`/`list()` outputs to prevent cross-test pollution.
- 10 dedicated isolation tests were added to verify no mutation leakage.

### Application

- Any in-memory repository or cache used for testing should deepcopy on both ingress and egress.
- Add explicit isolation tests that verify stored objects cannot be mutated by callers.
- This pattern applies to any language/framework where test doubles hold mutable state.

---

## LRN-005: Constructor DI over dependency_overrides for FastAPI Testing

**Tags:** testing, fastapi, dependency-injection, patterns
**Source:** v004/01-test-foundation/002-dependency-injection

### Context

FastAPI's `dependency_overrides` dict is the standard approach for replacing dependencies in tests, but it has drawbacks: it's global mutable state, requires cleanup, and the override mechanism is opaque.

### Learning

Use constructor-based dependency injection via `create_app()` parameters instead of `dependency_overrides`. Dependencies check `app.state` first and fall back to constructing production instances when parameters are `None`. This makes the test wiring explicit and eliminates global mutable state.

### Evidence

- v004 Theme 01 Feature 002 (dependency-injection): Replaced 4 `dependency_overrides` entries with `create_app(video_repository=..., project_repository=..., clip_repository=...)` parameter injection.
- Zero test failures during migration.
- Pattern extended naturally in Theme 03 with `create_app(job_queue=...)`.

### Application

- Prefer constructor/factory parameters over global override mechanisms for test dependency injection.
- Keep production defaults (None -> construct real instance) so the same factory works for both production and test.
- This pattern composes well: each new injectable dependency is just another optional parameter.

---

## LRN-006: Builder Pattern with Dual Output Modes for Test Fixtures

**Tags:** testing, patterns, builder, fixtures
**Source:** v004/01-test-foundation/003-fixture-factory

### Context

Test suites need different levels of integration: unit tests want domain objects directly, while integration tests need to exercise the full HTTP stack.

### Learning

Implement test fixture factories with a builder pattern that supports two output modes: `build()` for creating domain objects directly (unit tests) and `create_via_api()` for exercising the full HTTP path (integration/blackbox tests). This avoids forcing a single testing style while providing consistent test data construction.

### Evidence

- v004 Theme 01 Feature 003 (fixture-factory): `ProjectFactory` with `.with_clip()` chaining, `build()` returning domain objects, and `create_via_api()` using TestClient.
- Theme 02 blackbox tests consumed `create_via_api()` for all integration tests.
- `build_with_clips()` provided `(project, videos, clips)` tuples for seeding InMemory repositories.

### Application

- Design test factories with at least two output modes: direct object construction and full-stack integration.
- Use builder/chaining pattern for readable, composable test data setup.
- Keep sync `seed()` helpers on test doubles to reduce async boilerplate in unit tests.

---

## LRN-007: Parity Tests Prevent Test Double Drift

**Tags:** testing, patterns, parity, test-doubles, contracts
**Source:** v004/01-test-foundation, 02-blackbox-contract/003-search-unification

### Context

InMemory test doubles can silently diverge from real implementations over time. Behavioral differences (e.g., search semantics, ordering, edge cases) mean tests pass against fakes but fail against real systems.

### Learning

Write explicit parity tests that run the same operations against both the InMemory test double and the real implementation, asserting identical results. These tests serve as a contract between the fake and real, catching drift automatically.

### Evidence

- v004 Theme 01: 8 InMemory vs SQLite parity tests for repository operations.
- v004 Theme 02 Feature 003 (search-unification): 7 parity tests caught that InMemory used substring matching while SQLite FTS5 used prefix matching. The parity tests drove the fix to per-token `startswith` semantics.
- Parity tests extended naturally as new features were added.

### Application

- For every InMemory/fake test double, add parity tests against the real implementation.
- Run parity tests as part of the standard test suite (not just occasionally).
- When a parity test fails, fix the fake to match the real — the real implementation is the source of truth.
- Document known behavioral differences that are intentionally not matched.

---

## LRN-008: Record-Replay with Strict Mode for External Dependency Testing

**Tags:** testing, patterns, record-replay, external-dependencies, contracts
**Source:** v004/02-blackbox-contract/002-ffmpeg-contract-tests

### Context

Testing against external dependencies (FFmpeg, APIs, databases) is slow and environment-dependent. Fake implementations risk diverging from real behavior.

### Learning

Use a three-tier executor pattern: Real (calls actual dependency), Recording (wraps Real and captures interactions), and Fake (replays recorded interactions). Add a `strict` mode to the Fake that verifies input arguments match the recording before replaying, catching cases where code changes cause different inputs to be sent to the dependency.

### Evidence

- v004 Theme 02 Feature 002 (ffmpeg-contract-tests): 21 parametrized tests across Real, Recording, and Fake FFmpeg executors.
- `strict=True` on FakeFFmpegExecutor verified args match recordings before replaying.
- Only 23 lines added to executor.py for strict mode — minimal code for significant verification.
- `@pytest.mark.requires_ffmpeg` separated environment-dependent tests from universal tests.

### Application

- For any external dependency wrapper, implement the Real/Recording/Fake trio.
- Add strict mode to fakes for argument verification during testing.
- Use pytest markers to separate tests requiring real dependencies from those using fakes.
- This pattern scales to any external dependency (APIs, databases, file systems).

---

## LRN-009: Handler Registration Pattern for Generic Job Queues

**Tags:** architecture, patterns, job-queue, dependency-injection
**Source:** v004/03-async-scan/001-job-queue-infrastructure

### Context

Job queue systems need to route different job types to different handler functions. Common approaches include configuration files, decorator-based registration, or class hierarchies.

### Learning

Use a `register_handler(job_type, handler_fn)` method on the queue that wires job types to async functions at startup. This keeps routing explicit, avoids a separate handler registry module, and fails immediately with a clear error for unregistered job types. Combine with a factory function pattern (e.g., `make_scan_handler(repo)`) to inject dependencies into handlers at registration time.

### Evidence

- v004 Theme 03 Feature 001 (job-queue-infrastructure): `AsyncioJobQueue.register_handler()` wired job types to handlers.
- `make_scan_handler()` factory captured dependencies at registration time, keeping handlers testable in isolation.
- `InMemoryJobQueue` also supported handler registration for deterministic test execution.
- Jobs submitted without a registered handler failed immediately with a descriptive error.

### Application

- Prefer explicit registration over convention-based or configuration-based routing.
- Use factory functions to inject dependencies into handlers rather than having handlers reach into global state.
- Ensure unregistered job types fail fast with clear error messages.
- Apply the same registration pattern to both production and test queue implementations.

---

## LRN-010: Prefer stdlib asyncio.Queue over External Queue Dependencies

**Tags:** architecture, asyncio, dependencies, simplicity
**Source:** v004/03-async-scan (cross-theme learning)

### Context

Job queue implementations often default to external systems (Redis, RabbitMQ, arq) even when the application's scale doesn't require them. This adds deployment complexity and external dependencies.

### Learning

For applications with modest job queue requirements (single-worker, in-process), use Python's stdlib `asyncio.Queue` with a producer-consumer pattern instead of external queue systems. This eliminates an external dependency, simplifies deployment, and integrates naturally with FastAPI's lifespan context manager. Scale up to external queues only when demonstrated need arises.

### Evidence

- v004 Theme 03: Replaced planned arq/Redis dependency with `asyncio.Queue`. The single-worker producer-consumer pattern meets all current requirements.
- The version retrospective explicitly called this out as a cross-theme learning.
- Design documents were updated to replace arq/Redis references with asyncio.Queue.

### Application

- Start with stdlib solutions (asyncio.Queue, threading.Queue) before reaching for external dependencies.
- Design the queue protocol/interface generically so external implementations can be swapped in later if needed.
- Use InMemoryJobQueue (synchronous execution) for testing, AsyncioJobQueue (background worker) for production.
- This is a specific application of the general principle: avoid external dependencies until demonstrated need.

---

## LRN-011: Python Business Logic, Rust Input Safety in Hybrid Architectures

**Tags:** architecture, rust, python, hybrid, security, boundaries
**Source:** v004/04-security-performance (cross-theme learning)

### Context

In hybrid Python/Rust architectures, the boundary between what belongs in each language can be unclear, especially for validation and security concerns.

### Learning

Maintain a clean architectural boundary: Rust owns low-level input sanitization (null bytes, malformed strings, type validation), Python owns business policy (allowed paths, authentication, authorization, business rules). This separation ensures Rust code remains reusable across contexts while Python handles domain-specific decisions that may change with business requirements.

### Evidence

- v004 Theme 04 Feature 001 (security-audit): Rust's `validate_path` intentionally only checks for empty/null — it doesn't enforce business logic like allowed scan roots. `ALLOWED_SCAN_ROOTS` was correctly added in the Python scan service.
- Performance benchmarks confirmed Rust's value is correctness and type safety, not raw speed (PyO3 FFI overhead makes simple Rust operations 7-10x slower than Python equivalents).
- The version retrospective identified this as a key cross-theme learning.

### Application

- Rust layer: type safety, input sanitization, string processing, compute-heavy operations.
- Python layer: business rules, policy enforcement, configuration, HTTP routing.
- Don't put business rules in Rust — they change more frequently and are harder to modify.
- Justify Rust usage by safety/correctness benefits, not performance assumptions.

---

## LRN-012: PyO3 FFI Overhead Makes Rust Slower for Simple Operations

**Tags:** performance, rust, pyo3, ffi, benchmarking
**Source:** v004/04-security-performance/002-performance-benchmark

### Context

It's tempting to assume Rust will be faster than Python for all operations in a hybrid architecture. However, the FFI boundary introduces overhead that dominates for simple operations.

### Learning

PyO3 FFI overhead makes Rust 7-10x slower than Python for simple arithmetic and validation operations, and 3.5-4.8x slower for simple range operations. Rust is only faster for string-heavy processing (1.9x faster for `escape_filter_text`). Use Rust for operations where it provides clear computational or safety value, not as a blanket performance optimization.

### Evidence

- v004 Theme 04 Feature 002 (performance-benchmark): 7 benchmarks across 4 categories with consistent methodology (100 warmup, 10 runs, mean/median/stdev).
- Timeline arithmetic: Rust 7-10x slower due to FFI overhead.
- Range operations: Rust 3.5-4.8x slower.
- Path validation: Rust 8.3x slower.
- String escaping: Rust 1.9x faster (the one case where Rust wins on performance).

### Application

- Profile before assuming Rust will be faster — FFI overhead is significant for simple operations.
- Reserve Rust for operations where safety, correctness, or string processing justify the overhead.
- For performance-sensitive hot paths with simple logic, Python-native implementations may be faster.
- Use benchmarks with seeded random data for reproducible performance comparisons.

---

## LRN-013: Progressive Coverage Thresholds for Bootstrapping Enforcement

**Tags:** ci, coverage, process, thresholds
**Source:** v004/05-devex-coverage/002-rust-coverage

### Context

When adding coverage enforcement to a codebase for the first time (especially for a secondary language like Rust in a polyglot project), setting the target threshold immediately may cause false CI failures if the actual baseline is unknown.

### Learning

Set an initial progressive threshold below the target, then ratchet it up once CI confirms the actual baseline. Document both the current threshold and the target clearly. This avoids blocking development with false failures while still establishing the enforcement mechanism.

### Evidence

- v004 Theme 05 Feature 002 (rust-coverage): Rust coverage threshold set to 75% initially with documented target of 90%. Investigation estimated baseline at 75-90% but exact value needed CI confirmation.
- The retrospective explicitly noted this as a follow-up action: ratchet to 90% after 2-3 CI runs confirm the baseline.

### Application

- When adding coverage enforcement to a new codebase or language, start with a conservative threshold.
- Document the current threshold, target threshold, and the plan to ratchet up.
- Ratchet thresholds upward after confirming the baseline over several CI runs.
- This applies to any CI-enforced metric (coverage, lint score, performance budget).

---

## LRN-014: Template-Driven Process Improvements Over Standalone Documentation

**Tags:** process, templates, documentation, adoption
**Source:** v004/05-devex-coverage/001-property-test-guidance

### Context

Process improvements (like adopting property testing or adding quality checklists) can be documented as standalone guides, but adoption depends on developers discovering and following them.

### Learning

Embed process improvements directly into the templates that developers already use (requirements templates, implementation plan templates, design documents) rather than writing standalone documentation. This ensures the improvement becomes part of the standard workflow without relying on developers finding separate docs.

### Evidence

- v004 Theme 05 Feature 001 (property-test-guidance): Property test guidance was embedded into `02-REQUIREMENTS.md` and `03-IMPLEMENTATION-PLAN.md` templates with a concrete ID format (PT-xxx) and expected test count tracking.
- The version retrospective called this out as a cross-theme process improvement.
- Contrast with standalone documentation that can be easily overlooked.

### Application

- When introducing a new practice, modify the templates/checklists that people already follow.
- Include concrete formats (ID schemes, section headings) so the practice is actionable, not aspirational.
- This applies to any workflow improvement: code review checklists, security considerations, performance budgets.

---

## LRN-015: Single-Matrix CI Jobs for Expensive Operations

**Tags:** ci, performance, process, github-actions
**Source:** v004/05-devex-coverage/002-rust-coverage

### Context

CI pipelines with OS/language version matrices multiply job count. Expensive operations (coverage instrumentation, benchmarks, artifact generation) running across the full matrix waste resources and slow down feedback.

### Learning

Run expensive CI operations (coverage with instrumentation, benchmarks, artifact generation) as separate single-matrix jobs on a single platform (e.g., ubuntu-latest only) rather than across the full OS/Python version matrix. This keeps CI fast while still enforcing the check. Use the `ci-status` aggregation job pattern to make these jobs required without blocking the matrix.

### Evidence

- v004 Theme 05 Feature 002 (rust-coverage): `cargo-llvm-cov` runs only on ubuntu-latest as an independent `rust-coverage` job, not across the full OS/Python matrix.
- The `ci-status` job depends on `rust-coverage` along with the test matrix, allowing branch protection to require a single check.
- CI remained fast despite adding coverage instrumentation.

### Application

- Keep the test matrix for correctness verification across platforms.
- Run expensive instrumentation (coverage, ASAN, benchmarks) on a single platform in a separate job.
- Use a CI aggregation job to gate merges on all required checks.
- This pattern applies to any CI operation where the cost of running across the matrix exceeds the value.

---

## LRN-016: Validate Acceptance Criteria Against Codebase During Design

**Tags:** process, design, requirements, validation
**Source:** v004/01-test-foundation/003-fixture-factory, version retrospective

### Context

Feature requirements are typically written during design phase before implementation begins. If requirements reference domain models, APIs, or capabilities that don't yet exist, the implementing developer discovers unachievable criteria only during execution.

### Learning

Validate acceptance criteria against the actual codebase during design, not execution. Check that referenced domain models, APIs, dependencies, and capabilities exist before finalizing requirements. Mark criteria that depend on unimplemented prerequisites as explicitly deferred with a stated dependency.

### Evidence

- v004 Theme 01 Feature 003 (fixture-factory): FR-3 (`with_text_overlay()`) was unachievable because the TextOverlay domain model didn't exist. This was only discovered during implementation.
- The version retrospective elevated this to a top-level process improvement recommendation.
- Both the theme and version retrospectives recommended design-time validation.

### Application

- During design review, grep the codebase for referenced types/APIs/models.
- For each acceptance criterion, verify the preconditions are met.
- Mark unachievable criteria as "Deferred: depends on [specific prerequisite]" rather than including them as pass/fail.
- This prevents wasted implementation effort and confusing completion reports with N/A criteria.

---

## LRN-017: Empty Allowlist Means Unrestricted as Backwards-Compatible Default

**Tags:** security, configuration, backwards-compatibility, patterns
**Source:** v004/04-security-performance/001-security-audit

### Context

When adding restrictive configuration settings to an existing system (e.g., allowed paths, permitted origins, enabled features), choosing the right default behavior is critical for backwards compatibility.

### Learning

Use the convention "empty list = unrestricted" for allowlist-style configuration settings. This preserves backwards compatibility for existing deployments while letting production environments explicitly lock down access. Document this convention clearly and recommend restrictive configuration for production.

### Evidence

- v004 Theme 04 Feature 001 (security-audit): `ALLOWED_SCAN_ROOTS = []` defaults to "all paths allowed", avoiding breakage for existing users. Production deployments are advised to configure specific roots.
- The retrospective noted this as a reusable pattern for future restrictive settings.

### Application

- For any new allowlist setting, default to empty = unrestricted.
- Document the security implication of the default clearly.
- Provide recommended production values in deployment documentation.
- Consider logging a warning at startup when running with the unrestricted default in non-development environments.

---

## LRN-018: Audit-Then-Fix Is More Efficient Than Blanket Changes

**Tags:** process, code-quality, auditing, pragmatism
**Source:** v004/05-devex-coverage/003-coverage-gap-fixes

### Context

When addressing code quality issues (coverage exclusions, lint suppressions, tech debt), there's a temptation to make blanket changes or remove all suppressions at once.

### Learning

Audit first, then fix only what needs fixing. Catalogue all instances, evaluate each for justification, and only remediate the unjustified ones. This prevents unnecessary churn and ensures that legitimate suppressions are preserved and documented.

### Evidence

- v004 Theme 05 Feature 003 (coverage-gap-fixes): Audited 21 exclusions (`pragma: no cover`, `type: ignore`, `noqa`). Only 1 of 21 needed remediation (the `pragma: no cover` on ImportError fallback). The other 20 were properly justified.
- Added group-level justification comments to document why existing suppressions are correct.
- The retrospective explicitly called this out as a discovered pattern.

### Application

- Before removing lint/coverage suppressions, catalogue them all first.
- Evaluate each suppression for justification.
- Add documentation to justified suppressions if they lack explanation.
- Only remediate unjustified suppressions — don't create unnecessary churn.
- This approach applies to any codebase cleanup: tech debt, deprecated API usage, security warnings.

---

## LRN-019: Build Infrastructure First in Sequential Version Planning

**Tags:** process, planning, architecture, sequencing
**Source:** v004 version retrospective (cross-theme learning)

### Context

When planning a version with multiple themes, the ordering of themes matters. Some themes produce infrastructure consumed by later themes, while others are independent.

### Learning

Sequence "infrastructure" themes (test doubles, DI patterns, fixture factories) before "consumer" themes (feature tests, security tests, integration tests). The upfront investment in testing infrastructure pays off immediately when subsequent themes consume it without friction. Design independent features within themes whenever possible to avoid sequential bottlenecks.

### Evidence

- v004: Theme 01 (test foundation) was consumed by every subsequent theme. Theme 02 used DI pattern and InMemory doubles. Theme 03 extended create_app() with job_queue. Theme 04 used fixture infrastructure for security tests.
- The version retrospective explicitly validated this "build infrastructure first" sequencing strategy.
- Independent features within themes (Themes 02, 04, 05) executed cleaner than sequential features (Themes 01, 03).

### Application

- Place infrastructure/foundation themes at the beginning of version plans.
- Within themes, prefer independent features over sequential chains when possible.
- When sequential ordering is necessary, use handoff documents between features to provide clear context.
- This applies to any multi-theme development plan.
