# Requirements — rust-coverage

## Goal

Configure llvm-cov for Rust workspace with CI integration and threshold enforcement.

## Background

Rust code coverage is not tracked despite ~160 tests across 12 source files. AGENTS.md specifies 90% Rust coverage target. R6 investigation estimated baseline at 75-90%. U5 resolved: use `cargo-llvm-cov` on single CI matrix combo (ubuntu-latest + Python 3.12). Upload lcov report as artifact.

## Functional Requirements

| ID | Requirement | Backlog |
|----|-------------|---------|
| FR-1 | `cargo-llvm-cov` configured for Rust workspace | BL-010 |
| FR-2 | Coverage reports generated during CI | BL-010 |
| FR-3 | Coverage threshold enforced (target 90%, progressive if baseline < 90%) | BL-010 |
| FR-4 | Coverage visible in CI artifacts | BL-010 |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Coverage runs on single CI matrix combo only (ubuntu-latest + Python 3.12) |
| NFR-2 | Coverage step does not slow down other CI matrix jobs |
| NFR-3 | lcov report format for compatibility with coverage tools |

## Out of Scope

- Coverage dashboard or badge integration
- Coverage for PyO3 binding code (Python-side covered by pytest)
- Combined Python + Rust coverage report

## Test Requirements

| Type | Description | Est. Count |
|------|-------------|------------|
| CI | llvm-cov generates coverage report for Rust workspace | (CI config) |
| CI | Coverage threshold enforced | (CI config) |
