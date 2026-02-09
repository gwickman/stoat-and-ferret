## Context

CI pipelines with OS/language version matrices multiply job count. Expensive operations (coverage instrumentation, benchmarks, artifact generation) running across the full matrix waste resources and slow down feedback.

## Learning

Run expensive CI operations (coverage with instrumentation, benchmarks, artifact generation) as separate single-matrix jobs on a single platform (e.g., ubuntu-latest only) rather than across the full OS/Python version matrix. This keeps CI fast while still enforcing the check. Use the `ci-status` aggregation job pattern to make these jobs required without blocking the matrix.

## Evidence

- v004 Theme 05 Feature 002 (rust-coverage): `cargo-llvm-cov` runs only on ubuntu-latest as an independent `rust-coverage` job, not across the full OS/Python matrix.
- The `ci-status` job depends on `rust-coverage` along with the test matrix, allowing branch protection to require a single check.
- CI remained fast despite adding coverage instrumentation.

## Application

- Keep the test matrix for correctness verification across platforms.
- Run expensive instrumentation (coverage, ASAN, benchmarks) on a single platform in a separate job.
- Use a CI aggregation job to gate merges on all required checks.
- This pattern applies to any CI operation where the cost of running across the matrix exceeds the value.