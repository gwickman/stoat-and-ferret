# Implementation Plan — rust-coverage

## Overview

Configure `cargo-llvm-cov` for the Rust workspace and integrate into CI with threshold enforcement.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|--------|
| Modify | `.github/workflows/test.yml` | Add Rust coverage step |
| Create | `rust/stoat_ferret_core/.cargo/config.toml` | llvm-cov configuration (if needed) |

## Implementation Stages

### Stage 1: Measure Baseline
Run `cargo llvm-cov --workspace` locally to establish baseline coverage percentage. This determines the initial threshold.

### Stage 2: CI Integration
Add a Rust coverage step to the CI workflow:
- Only runs on ubuntu-latest + Python 3.12 matrix entry
- Install `cargo-llvm-cov` tool
- Run `cargo llvm-cov --workspace --lcov --output-path lcov.info`
- Upload lcov.info as CI artifact
- Enforce threshold with `--fail-under-lines`

### Stage 3: Threshold Setting
If baseline >= 90%: set threshold to 90%.
If baseline < 90%: set progressive threshold at baseline value, document plan to ratchet up.

## Quality Gates

- Coverage report generates successfully locally
- CI step passes on ubuntu-latest
- Threshold enforced (fail if below)
- lcov artifact uploaded

## Risks

| Risk | Mitigation |
|------|------------|
| R6: Baseline below 90% | Progressive threshold with documented ratchet plan |
| llvm-cov installation issues in CI | Use cargo-binstall or pre-built binaries |

## Commit Message

```
feat: add Rust code coverage with llvm-cov and CI integration
```