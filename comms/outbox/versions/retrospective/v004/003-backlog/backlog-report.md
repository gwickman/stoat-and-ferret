# v004 Backlog Verification — Detailed Report

| Backlog Item | Title | Feature | Status Before | Action | Status After |
|---|---|---|---|---|---|
| BL-009 | Add property test guidance to feature design template | 05-devex-coverage/001-property-test-guidance | open | Completed (v004/devex-coverage) | completed |
| BL-010 | Configure Rust code coverage with llvm-cov | 05-devex-coverage/002-rust-coverage | open | Completed (v004/devex-coverage) | completed |
| BL-012 | Fix coverage reporting gaps for ImportError fallback | 05-devex-coverage/003-coverage-gap-fixes | open | Completed (v004/devex-coverage) | completed |
| BL-014 | Add Docker-based local testing option | 05-devex-coverage/004-docker-testing | open | Completed (v004/devex-coverage) | completed |
| BL-016 | Unify InMemory vs FTS5 search behavior | 02-blackbox-contract/003-search-unification | open | Completed (v004/blackbox-contract) | completed |
| BL-020 | Implement InMemory test doubles for Projects and Jobs | 01-test-foundation/001-inmemory-test-doubles | open | Completed (v004/test-foundation) | completed |
| BL-021 | Add dependency injection to create_app() for test wiring | 01-test-foundation/002-dependency-injection | open | Completed (v004/test-foundation) | completed |
| BL-022 | Build fixture factory with builder pattern for test data | 01-test-foundation/003-fixture-factory | open | Completed (v004/test-foundation) | completed |
| BL-023 | Implement black box test scenario catalog | 02-blackbox-contract/001-blackbox-test-catalog | open | Completed (v004/blackbox-contract) | completed |
| BL-024 | Contract tests with real FFmpeg for executor fidelity | 02-blackbox-contract/002-ffmpeg-contract-tests | open | Completed (v004/blackbox-contract) | completed |
| BL-025 | Security audit of Rust path validation and input sanitization | 04-security-performance/001-security-audit | open | Completed (v004/security-performance) | completed |
| BL-026 | Rust vs Python performance benchmark for core operations | 04-security-performance/002-performance-benchmark | open | Completed (v004/security-performance) | completed |
| BL-027 | Async job queue for scan operations | 03-async-scan/001-job-queue-infrastructure, 002-async-scan-endpoint, 003-scan-doc-updates | open | Completed (v004/async-scan) | completed |

## Notes

- BL-027 was referenced by 3 features in the async-scan theme (job-queue-infrastructure, async-scan-endpoint, scan-doc-updates), reflecting its scope as a multi-feature backlog item.
- All other backlog items had a 1:1 mapping to their implementing feature.
- No orphaned open items referencing v004 were found among the 29 remaining open backlog items.
