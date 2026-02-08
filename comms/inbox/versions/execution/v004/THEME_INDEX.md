# v004 Theme Index

## Execution Order

Execute themes in order. Each theme must complete before starting the next.

### Theme 01: test-foundation

**Path:** `comms/inbox/versions/execution/v004/01-test-foundation/`
**Goal:** Establish core testing infrastructure — test doubles, dependency injection, and fixture factories — that all other themes depend on.

**Features:**

- 001-inmemory-test-doubles: _Feature description_
- 002-dependency-injection: _Feature description_
- 003-fixture-factory: _Feature description_
### Theme 02: blackbox-contract

**Path:** `comms/inbox/versions/execution/v004/02-blackbox-contract/`
**Goal:** Implement end-to-end black box tests, verified fakes for FFmpeg executors, and unified search behavior for test consistency.

**Features:**

- 001-blackbox-test-catalog: _Feature description_
- 002-ffmpeg-contract-tests: _Feature description_
- 003-search-unification: _Feature description_
### Theme 03: async-scan

**Path:** `comms/inbox/versions/execution/v004/03-async-scan/`
**Goal:** Replace synchronous blocking scan with async job queue pattern, enabling progress tracking and non-blocking API behavior.

**Features:**

- 001-job-queue-infrastructure: _Feature description_
- 002-async-scan-endpoint: _Feature description_
- 003-scan-doc-updates: _Feature description_
### Theme 04: security-performance

**Path:** `comms/inbox/versions/execution/v004/04-security-performance/`
**Goal:** Complete M1.9 quality verification — security audit of Rust sanitization and performance benchmarks validating the hybrid architecture.

**Features:**

- 001-security-audit: _Feature description_
- 002-performance-benchmark: _Feature description_
### Theme 05: devex-coverage

**Path:** `comms/inbox/versions/execution/v004/05-devex-coverage/`
**Goal:** Improve developer tooling, testing processes, and coverage infrastructure.

**Features:**

- 001-property-test-guidance: _Feature description_
- 002-rust-coverage: _Feature description_
- 003-coverage-gap-fixes: _Feature description_
- 004-docker-testing: _Feature description_
## Notes

- Each feature folder contains requirements.md and implementation-plan.md
- Output documents go to comms/outbox/
- Follow AGENTS.md for implementation process
