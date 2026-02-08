# Draft Verification Checklist

- [x] manifest.json is valid JSON with all required fields
- [x] Every theme in manifest has a corresponding folder under drafts/
- [x] Every feature has requirements.md and implementation-plan.md
- [x] VERSION_DESIGN.md and THEME_INDEX.md exist
- [x] THEME_INDEX feature lines match format `- \d{3}-[\w-]+: .+`
- [x] No placeholder text
- [x] All backlog IDs from manifest appear in at least one requirements.md
- [x] No theme or feature slug starts with a digit prefix
- [x] Backlog IDs cross-referenced against Task 002

## Backlog ID Coverage

| Backlog ID | Requirements File(s) |
|------------|---------------------|
| BL-020 | test-foundation/inmemory-test-doubles/requirements.md |
| BL-021 | test-foundation/dependency-injection/requirements.md |
| BL-022 | test-foundation/fixture-factory/requirements.md |
| BL-023 | blackbox-contract/blackbox-test-catalog/requirements.md |
| BL-024 | blackbox-contract/ffmpeg-contract-tests/requirements.md |
| BL-025 | security-performance/security-audit/requirements.md |
| BL-026 | security-performance/performance-benchmark/requirements.md |
| BL-027 | async-scan/job-queue-infrastructure/requirements.md, async-scan/async-scan-endpoint/requirements.md, async-scan/scan-doc-updates/requirements.md |
| BL-009 | devex-coverage/property-test-guidance/requirements.md |
| BL-010 | devex-coverage/rust-coverage/requirements.md |
| BL-012 | devex-coverage/coverage-gap-fixes/requirements.md |
| BL-014 | devex-coverage/docker-testing/requirements.md |
| BL-016 | blackbox-contract/search-unification/requirements.md |

All 13 backlog IDs covered. No gaps.

## Slug Verification

Theme slugs (no digit prefixes): test-foundation, blackbox-contract, async-scan, security-performance, devex-coverage

Feature slugs (no digit prefixes): inmemory-test-doubles, dependency-injection, fixture-factory, blackbox-test-catalog, ffmpeg-contract-tests, search-unification, job-queue-infrastructure, async-scan-endpoint, scan-doc-updates, security-audit, performance-benchmark, property-test-guidance, rust-coverage, coverage-gap-fixes, docker-testing
