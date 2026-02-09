Read AGENTS.md first and follow all instructions there.

## Objective

Extract transferable learnings from all completion reports and theme retrospectives for stoat-and-ferret version v004, then save them via the learnings system.

## Tasks

### 1. Read All Completion Reports
Read every completion report for v004. The themes and features are:
- 01-test-foundation: 001-inmemory-test-doubles, 002-dependency-injection, 003-fixture-factory
- 02-blackbox-contract: 001-blackbox-test-catalog, 002-ffmpeg-contract-tests, 003-search-unification
- 03-async-scan: 001-job-queue-infrastructure, 002-async-scan-endpoint, 003-scan-doc-updates
- 04-security-performance: 001-security-audit, 002-performance-benchmark
- 05-devex-coverage: 001-property-test-guidance, 002-rust-coverage, 003-coverage-gap-fixes, 004-docker-testing

Path pattern: comms/outbox/versions/execution/v004/<theme>/<feature>/completion-report.md

For each report, identify: patterns that worked well, approaches that failed, decision rationale worth preserving, debugging techniques.

### 2. Read All Theme Retrospectives
Read every theme retrospective: comms/outbox/versions/execution/v004/<theme>/retrospective.md

### 3. Read Version Retrospective
Read: comms/outbox/versions/execution/v004/retrospective.md

### 4. Deduplicate and Filter
Remove duplicates, implementation-specific details, version-specific references. Keep: transferable patterns, failure modes, decision frameworks, debugging approaches.

### 5. Save Learnings
For each unique learning, call save_learning() with:
- project="stoat-and-ferret"
- title, content (with Context/Learning/Evidence/Application sections), tags, source, summary

### 6. Check Existing Learnings for Updates
Call list_learnings(project="stoat-and-ferret") and note any reinforced learnings.

## Output Requirements

Save outputs to comms/outbox/exploration/v004-retro-006-learnings/:

### README.md (required)
First paragraph: Learnings summary (X new learnings saved, Y existing reinforced).

Then:
- **New Learnings**: Table of title, tags, source
- **Reinforced Learnings**: Existing learnings that got additional evidence
- **Filtered Out**: Count and categories of items filtered

### learnings-detail.md
For each learning saved: title, tags, source document, full content saved.

Do NOT commit — the calling prompt handles commits. Results folder: v004-retro-006-learnings.