# THEME DESIGN — 04: Security & Performance Verification

## Goal

Complete M1.9 quality verification — security audit of Rust sanitization and performance benchmarks validating the hybrid architecture.

## Design Artifacts

- Refined logical design: `comms/outbox/versions/design/v004/006-critical-thinking/refined-logical-design.md` (Theme 04 section)
- Codebase patterns: `comms/outbox/versions/design/v004/004-research/codebase-patterns.md` (Rust Sanitization section)
- Test strategy: `comms/outbox/versions/design/v004/005-logical-design/test-strategy.md` (Theme 04 section)
- Risk assessment: `comms/outbox/versions/design/v004/006-critical-thinking/risk-assessment.md` (R4, U2)

## Features

| # | Feature | Backlog | Dependencies |
|---|---------|---------|-------------|
| 1 | security-audit | BL-025 | None |
| 2 | performance-benchmark | BL-026 | None |

## Dependencies

- **Upstream**: None. Both features are independent.
- **Internal**: Features are independent of each other.
- **External**: None.

## Technical Approach

1. **Security audit** (BL-025): Audit Rust `validate_path` (only checks empty/null), `escape_filter_text` (8 special chars), and all validation functions. Known gap: no path traversal or symlink protection. Recommend `ALLOWED_SCAN_ROOTS` config + check in Python scan service (~20 lines). Produce audit document in `docs/` with findings. Implement critical remediation.
2. **Performance benchmark** (BL-026): Create `benchmarks/` directory with scripts comparing Rust vs Python for 3+ operations. Candidates: timeline position arithmetic, filter string escaping, path validation. Document speedup ratios.

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| R4: Security audit scope creep | Low (resolved) | Gap is bounded — ~20 lines Python fix for scan roots |
| U2: Benchmark operation selection | TBD | Candidates identified; profile at implementation time |