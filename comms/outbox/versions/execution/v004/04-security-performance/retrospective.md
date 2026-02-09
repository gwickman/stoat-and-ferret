# Theme Retrospective — 04: Security & Performance Verification

## Theme Summary

Theme 04 completed the M1.9 quality verification milestone by auditing Rust sanitization functions for security vulnerabilities and benchmarking Rust vs Python performance across the hybrid architecture. Two independent features were delivered:

1. **Security audit** — Reviewed all 8 Rust sanitization/validation functions against OWASP attack vectors (path traversal, null byte injection, shell injection). Identified and remediated the `validate_path` gap by adding `ALLOWED_SCAN_ROOTS` configuration with `validate_scan_path()` enforcement in the Python scan service. Published structured audit findings in `docs/design/09-security-audit.md` and added 35 security tests.
2. **Performance benchmark** — Created a `benchmarks/` package comparing Rust vs Python for 7 operations across 4 categories (timeline arithmetic, string escaping, range operations, path validation). Documented speedup ratios in `docs/design/10-performance-benchmarks.md`, confirming that Rust's value is in safety/correctness rather than raw speed for most operations.

Both features passed all quality gates (ruff, mypy, pytest) and met their acceptance criteria. The theme added 35 new security tests while maintaining 92.71% coverage across 564 passing tests.

## Feature Results

| # | Feature | Acceptance | Quality Gates | Tests Added | Status |
|---|---------|------------|---------------|-------------|--------|
| 1 | security-audit | 4/4 PASS | All PASS | 35 | Complete |
| 2 | performance-benchmark | 3/3 PASS | All PASS | 0 (benchmarks, not tests) | Complete |

**Totals:** 7/7 acceptance criteria passed. 35 new tests. 0 regressions.

## Key Learnings

### What Went Well

- **Independent features enabled parallel-ready execution.** Unlike Theme 03's sequential chain, both features had zero dependencies on each other. This structure is ideal for parallelization and meant neither feature could block the other.
- **Python-layer remediation was the right architectural call.** The `validate_path` Rust function intentionally only checks for empty/null — it doesn't enforce business logic like allowed scan roots. Adding `ALLOWED_SCAN_ROOTS` in the Python scan service maintained the clean separation: Rust owns low-level input safety, Python owns business policy.
- **Benchmark results validated the hybrid architecture rationale.** The benchmarks showed Rust is faster only for string-heavy operations (1.9x for `escape_filter_text`) while PyO3 FFI overhead makes Rust slower for simple operations (7-10x for arithmetic). This confirms the Rust layer's justification is type safety and correctness guarantees, not performance — an important finding for future architectural decisions.
- **Security test coverage was thorough.** 35 tests across 5 attack categories (path traversal, null bytes, shell injection, whitelist bypass, FFmpeg filter injection) provide strong regression protection for the security boundary.

### Patterns Discovered

- **Empty-allowlist-means-all-allowed as a backwards-compatible default.** Setting `allowed_scan_roots = []` to mean "unrestricted" avoids breaking existing deployments while letting production environments lock down paths. This is a common pattern worth reusing for future restrictive settings.
- **`@lru_cache` on settings means config is startup-time only.** The `get_settings()` function caches settings, so `ALLOWED_SCAN_ROOTS` changes require a server restart. This is an acceptable tradeoff for simplicity but worth documenting clearly.
- **Seeded random data for reproducible benchmarks.** Using deterministic test data generation ensures benchmark ratios are comparable across runs without requiring identical hardware.

### What Could Improve

- **No quality-gaps documents were generated.** This is the third consecutive theme where `quality-gaps.md` files were not produced during feature execution. The completion reports continue to serve as the primary quality record.
- **Benchmark results are hardware-dependent.** While relative ratios (Rust vs Python) are stable, absolute timings vary by machine. Consider adding CI-based benchmark tracking if performance regression detection becomes important.

## Technical Debt

| Item | Source | Priority | Notes |
|------|--------|----------|-------|
| `ALLOWED_SCAN_ROOTS` + auth integration | Feature 1 | Low | If authentication is added, scan root restrictions should work in conjunction with user-level permissions |
| Settings `@lru_cache` prevents runtime config changes | Feature 1 | Low | Config changes require server restart; acceptable for now but may need hot-reload for production |
| No CI benchmark tracking | Feature 2 | Low | Benchmarks are manual-run only; add CI benchmark step if performance regression detection is needed |
| PyO3 FFI overhead for simple operations | Feature 2 | Info | 7-10x overhead for arithmetic operations is a known cost of the hybrid architecture; not actionable unless hot-path profiling reveals bottlenecks |

## Recommendations

1. **For future security work:** The `tests/test_security/` package is structured for expansion. New attack vectors or endpoints can be tested by adding modules to this package following the existing fixture patterns in `conftest.py`.
2. **For production deployment:** Configure `ALLOWED_SCAN_ROOTS` to restrict scan directories. The empty-list default permits all paths for development convenience but should be locked down in production.
3. **For performance-sensitive paths:** Only use Rust for operations where it provides clear value (string processing, complex validation). For simple arithmetic or operations with minimal computation, Python-native implementations avoid PyO3 FFI overhead.
4. **Quality-gaps generation:** This is now the third theme without `quality-gaps.md` files. Either formalize their generation as a required step or remove them from the retrospective template.

## Metrics

- **Lines changed:** +1,767 / -1 across 21 files
- **Source files changed:** 3 (all modified)
- **Test files changed:** 4 (all created)
- **Benchmark files changed:** 8 (all created)
- **Doc files changed:** 2 (all created)
- **Final test count:** 564 passed, 15 skipped
- **Coverage:** 92.71%
- **Commits:** 2 (one per feature, via PR)
