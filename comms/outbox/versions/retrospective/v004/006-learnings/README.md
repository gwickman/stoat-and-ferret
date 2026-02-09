# v004 Learnings Extraction

Extracted 16 new transferable learnings (LRN-004 through LRN-019) from v004's 15 completion reports, 5 theme retrospectives, and 1 version retrospective. 1 existing learning (LRN-003: Security Validation Whitelist Pattern) was reinforced by new evidence from the security audit and empty-allowlist pattern.

## New Learnings

| ID | Title | Tags | Source |
|----|-------|------|--------|
| LRN-004 | Deepcopy Isolation for InMemory Test Doubles | testing, patterns, isolation, test-doubles | 01-test-foundation/001-inmemory-test-doubles |
| LRN-005 | Constructor DI over dependency_overrides for FastAPI Testing | testing, fastapi, dependency-injection, patterns | 01-test-foundation/002-dependency-injection |
| LRN-006 | Builder Pattern with Dual Output Modes for Test Fixtures | testing, patterns, builder, fixtures | 01-test-foundation/003-fixture-factory |
| LRN-007 | Parity Tests Prevent Test Double Drift | testing, patterns, parity, test-doubles, contracts | 01-test-foundation, 02-blackbox-contract/003 |
| LRN-008 | Record-Replay with Strict Mode for External Dependency Testing | testing, patterns, record-replay, external-dependencies, contracts | 02-blackbox-contract/002-ffmpeg-contract-tests |
| LRN-009 | Handler Registration Pattern for Generic Job Queues | architecture, patterns, job-queue, dependency-injection | 03-async-scan/001-job-queue-infrastructure |
| LRN-010 | Prefer stdlib asyncio.Queue over External Queue Dependencies | architecture, asyncio, dependencies, simplicity | 03-async-scan (cross-theme) |
| LRN-011 | Python Business Logic, Rust Input Safety in Hybrid Architectures | architecture, rust, python, hybrid, security, boundaries | 04-security-performance (cross-theme) |
| LRN-012 | PyO3 FFI Overhead Makes Rust Slower for Simple Operations | performance, rust, pyo3, ffi, benchmarking | 04-security-performance/002-performance-benchmark |
| LRN-013 | Progressive Coverage Thresholds for Bootstrapping Enforcement | ci, coverage, process, thresholds | 05-devex-coverage/002-rust-coverage |
| LRN-014 | Template-Driven Process Improvements Over Standalone Documentation | process, templates, documentation, adoption | 05-devex-coverage/001-property-test-guidance |
| LRN-015 | Single-Matrix CI Jobs for Expensive Operations | ci, performance, process, github-actions | 05-devex-coverage/002-rust-coverage |
| LRN-016 | Validate Acceptance Criteria Against Codebase During Design | process, design, requirements, validation | 01-test-foundation/003, version retrospective |
| LRN-017 | Empty Allowlist Means Unrestricted as Backwards-Compatible Default | security, configuration, backwards-compatibility, patterns | 04-security-performance/001-security-audit |
| LRN-018 | Audit-Then-Fix Is More Efficient Than Blanket Changes | process, code-quality, auditing, pragmatism | 05-devex-coverage/003-coverage-gap-fixes |
| LRN-019 | Build Infrastructure First in Sequential Version Planning | process, planning, architecture, sequencing | version retrospective (cross-theme) |

## Reinforced Learnings

| ID | Title | New Evidence |
|----|-------|-------------|
| LRN-003 | Security Validation Whitelist Pattern | v004 security audit confirmed the whitelist approach with `ALLOWED_SCAN_ROOTS`. The empty-allowlist-means-unrestricted default (LRN-017) extends this pattern with a backwards-compatible convention. |

## Filtered Out

**12 items filtered** across these categories:

- **Version-specific details (5):** Test count progressions (396 -> 455 -> 507 -> 529 -> 564 -> 571), specific file lists, PR numbers (#48-#62), coverage percentages by theme
- **Implementation-specific details (3):** Specific module paths (e.g., `src/stoat_ferret/jobs/queue.py`), specific method signatures, Pydantic model names
- **Duplicate observations (2):** "quality-gaps.md never generated" noted in all 5 themes — captured once as a process observation rather than a learning since the solution (enforce or remove) wasn't resolved
- **Non-transferable observations (2):** Specific technical debt items (get_repository alias, FTS5 multi-word phrase differences) that are codebase-specific fixes rather than transferable patterns
