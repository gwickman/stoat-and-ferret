# AGENTS.md - stoat-and-ferret

AI-driven video editor with hybrid Python/Rust architecture.

## Project Structure

```
stoat-and-ferret/
├── src/                    # Python source (FastAPI, orchestration)
│   └── stoat_ferret_core/  # Python package with type stubs for Rust bindings (_core.pyi)
├── rust/stoat_ferret_core/ # Rust crate (filters, timeline math, FFmpeg, expressions)
├── gui/                    # Frontend (React/TypeScript/Vite)
├── tests/                  # Python tests (pytest)
├── docs/design/            # Architecture and design documents
└── comms/                  # MCP communication folders
```

## Commands

```bash
# Development
uv sync                      # Install dependencies
uv run ruff check .          # Lint
uv run ruff format .         # Format
uv run mypy src/             # Type check
uv run pytest                # Test

# Frontend
cd gui
npm install                  # Install dependencies
npm run dev                  # Dev server (proxies API to :8765)
npm run build                # Production build to gui/dist/
npx vitest run               # Run tests

# Rust — run cargo commands from rust/stoat_ferret_core/
cd rust/stoat_ferret_core
cargo clippy -- -D warnings  # Lint
cargo test                   # Test

# maturin develop: run from the project ROOT, not from rust/stoat_ferret_core/
# (Running from the crate directory creates a conflicting package in site-packages)
maturin develop              # Build Python extension

# UAT (User Acceptance Testing)
uv pip install -e ".[uat]"                          # Install UAT dependencies
playwright install chromium                          # Download Chromium binary
python scripts/uat_runner.py --headless              # Run UAT headless (full build)
python scripts/uat_runner.py --headless --skip-build # Run UAT against running server

# Type Stubs
cd rust/stoat_ferret_core
cargo run --bin stub_gen     # Generate baseline stubs to .generated-stubs/
# Then verify: uv run python scripts/verify_stubs.py
```

## Windows (Git Bash)

In Git Bash (MSYS2) on Windows, always use `/dev/null` for output redirection — MSYS translates it to the Windows null device automatically. Do **not** use bare `nul` (the native Windows convention), because Git Bash interprets it as a literal filename and creates a file named `nul` in the working directory.

```bash
# Correct — /dev/null works in Git Bash on Windows
command > /dev/null 2>&1

# Wrong — creates a literal file named "nul"
command > nul
```

The project `.gitignore` already includes a `nul` entry as a safety net, but avoid creating it in the first place.

### Branch State Persistence

All git operations for a feature must be chained in a single bash invocation. MSYS2 does not persist branch state reliably across separate shell invocations.

```bash
# Correct — all operations chained in one call
git checkout -b feat/my-feature && git add src/ && git commit -m "feat: ..." && git push -u origin HEAD

# Risky — branch created in one shell, push in another may target wrong branch
git checkout -b feat/my-feature
# ... separate shell invocation ...
git push -u origin HEAD
```

Always run `git status` before `git push` to verify the current branch is correct.

### Structural Enforcement

The `/dev/null` vs `nul` convention is enforced via tooling at two levels:

1. **Pre-commit hook:** Runs on every commit; blocks commits containing `> nul` patterns in `.sh`, `.bash`, and `.yml` files. The hook uses `grep -I -F` (fixed-string literal mode `-F` for portability across GNU grep on Linux/CI and BSD grep on macOS). The `-I` flag skips binary files, preventing false positives on compiled artifacts.

2. **CI backup step:** Greps `.github/workflows/` and `scripts/` for `> nul` patterns at push time; blocks merge if violations found, catching any commits that bypassed the pre-commit hook.

To enable the hook locally, run:

```bash
pre-commit install
```

The hook configuration is defined in `.pre-commit-config.yaml` in the repository root.

## Type Stubs

Python type stubs for the Rust PyO3 bindings are maintained in `src/stoat_ferret_core/` (the `_core.pyi` file lives alongside the Python package).

**Manual vs Generated Stubs**: The stubs are manually maintained because `pyo3-stub-gen` generates incomplete stubs (class docstrings only, no method signatures). The generated stubs serve as a baseline for detecting new types added to Rust.

### Workflow After Modifying Rust API

1. Run stub generation:
   ```bash
   cd rust/stoat_ferret_core
   cargo run --bin stub_gen
   ```

   > **Warning — Do NOT copy stub_gen output wholesale.** Running
   > `cargo run --bin stub_gen` and copying its output file directly to
   > `src/stoat_ferret_core/_core.pyi` strips all hand-written `__new__`
   > constructors and produces 100+ mypy errors. Always use append-only
   > edits: restore from main and add only the new classes.

2. Verify stubs are complete:
   ```bash
   uv run python scripts/verify_stubs.py
   ```

3. If verification fails, update `src/stoat_ferret_core/_core.pyi` to include the missing types with proper method signatures.

4. Commit both the Rust changes and updated stubs.

**CI Enforcement**: The CI workflow runs `scripts/verify_stubs.py` to ensure manual stubs include all types from the generated stubs.

## Quality Gates

### Python (ruff, mypy, pytest)

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
uv run pytest tests/smoke/ -v --timeout=120 --no-cov
# Windows sandbox: UV_NO_CACHE=1 uv run pytest tests/smoke/ -v --timeout=120 --no-cov
# See docs/manual/smoke-test-harness.md for details
```

### Smoke Test Harness

See [docs/manual/smoke-test-harness.md](docs/manual/smoke-test-harness.md) for harness setup instructions, `STOAT_TEST_FFMPEG` usage, and discharge procedures for `deferred_post_merge` ACs.

### FFmpeg Gated CI Lane

The `ffmpeg-tests` CI job runs on `ubuntu-latest` with FFmpeg 8 (installed via `AnimMouse/setup-ffmpeg@v1`) and sets `STOAT_TEST_FFMPEG=1` to enable gated tests that are silently skipped in the standard `test` matrix:

```bash
STOAT_TEST_FFMPEG=1 uv run pytest tests/ --no-cov --timeout=120
```

To run gated tests locally:

```bash
STOAT_TEST_FFMPEG=1 uv run pytest tests/ --no-cov -v
```

BL-503's per-effect gated-contract DoD gate is enforced by the `ffmpeg-tests` CI lane. Any AC that cross-references BL-503's FFmpeg contract verification is gated on this lane passing.

The `ffmpeg-tests` job is non-required during the triage window — it is not in the `ci-status` needs array. Once the lane is stable it can be promoted to required by adding it to `ci-status.needs`.

### Frontend (TypeScript, Vitest)

```bash
cd gui
npx tsc -b                   # Type check
npx vitest run               # Run tests
```

### Rust (clippy, cargo test)

```bash
cd rust/stoat_ferret_core
cargo clippy -- -D warnings
cargo test
```

### OpenAPI Schema Sync

`gui/openapi.json` must stay in sync with the live FastAPI spec. CI enforces this via a boot-and-compare step, but failures are preventable by regenerating before every push when API routes or schemas change:

```bash
uv run python -m scripts.export_openapi
cd gui && npm run generate:types   # updates gui/src/generated/api-types.ts
```

Both commands must be run together — `export_openapi` updates `gui/openapi.json` while `generate:types` regenerates `gui/src/generated/api-types.ts` from it. If only `gui/openapi.json` appears in `git diff`, the second step was missed.

Run these commands any time you add, remove, or modify an API endpoint, Pydantic request/response model, or route decorator. Forgetting to regenerate is the most common cause of CI failures across versions.

### Coverage Thresholds

- Python: 80% minimum
- Rust: 90% minimum

## Security Audit Cadence

Security audits are conducted on a recurring schedule defined in `docs/security/audit-cadence.md`. Triggers include quarterly review, Python/FFmpeg/PyO3 major version upgrades, and new unsafe Rust patterns. Findings are filed as backlog items per the BL-filing pattern established in v043. See `docs/security/audit-cadence.md` for scope, deliverables, and review schedule.

## Coding Standards

### Python

- Type hints required on all public functions
- Docstrings required on all public modules, classes, and functions
- Follow existing patterns in codebase
- Use `from __future__ import annotations` for forward references

### Rust

- All public items must have doc comments
- No `unwrap()` in library code - use proper error handling
- Prefer returning `Result<T, E>` over panicking
- PyO3 bindings should have Python-friendly error messages

## Code Quality Principles

Default to KISS + YAGNI for new code. Refactor to DRY and SOLID (SRP/DIP/ISP baseline, LSP via substitutability tests) after duplication or change is demonstrated. Introduce OCP extension points when there's an evidenced extension requirement.

---

## Documentation Standards

### Configuration Documentation Rule

When a new `STOAT_*` environment variable is introduced in `src/stoat_ferret/api/settings.py`, the same backlog item must:

1. Add an entry for the variable in `docs/setup/04_configuration.md` (operator-facing reference covering name, type, default, valid range, and a plain-English description).
2. Add an entry for the variable in `docs/manual/configuration-reference.md` (security-focused operator guide covering production hazards, security implications, and recommended values).
3. Keep the `KNOWN_UNDOCUMENTED_SETTINGS_VARS` allowlist in `tests/security/test_audit.py` empty. The drift baseline is enforced as a frozenset; adding a variable without documenting it will fail the security audit probe.

This rule applies to all future `STOAT_*` variables, not just security-sensitive ones — uniform enforcement is cheaper than selective review and keeps the audit baseline at zero. The rule is forward-looking; existing gaps are closed in v045 (Feature 001 + Feature 002).

`docs/manual/configuration-reference.md` cross-references this section as the authoritative process anchor; do not duplicate the rule text elsewhere.

---

## Startup Ordering

### Startup Ordering Rule

New services and background tasks added to the `lifespan()` function in `src/stoat_ferret/api/app.py` must follow the 14-phase ordering contract:

- **New services** must initialize **after Phase 6** (database connection open, line 170) and **before Phase 9** (AuditLogger initialized, line 181). If the service depends on a repository, initialize after Phase 10 (repositories initialized, line 186).
- **New background tasks** must start **after Phase 12** (background job worker started, line 289) and **before Phase 13** (gate cleared, line 305). Do not start tasks that probe the application (e.g., via ASGITransport) before Phase 13.
- **Never** insert code that reads or writes the database before Phase 5 (Alembic migrations, line 167) completes — schema state is undefined until migrations apply.

See `docs/design/FRAMEWORK_CONTEXT.md` §3, Startup Initialization Sequence for the full 14-phase table and ordering constraints.

---

## Database Migrations

### Migration Safeguard Rule

All future migrations for audit or operational (append-only) tables must:

1. Use `CREATE TABLE IF NOT EXISTS table_name (...)` in the upgrade path — the `IF NOT EXISTS` clause is mandatory for idempotency.
2. Use `CREATE INDEX IF NOT EXISTS idx_name ON table(col)` for any accompanying indexes.
3. Never use `DROP TABLE` or any other destructive statement in the downgrade path. Downgrade for append-only tables is a no-op (`pass`), or may raise an explicit error if the schema version is critical.

**Rationale**: MigrationService self-heals by re-applying missing revisions on retry. `CREATE TABLE IF NOT EXISTS` makes re-application safe — a table that already exists is silently skipped. A destructive downgrade erases audit data, including the record of the downgrade itself, corrupting the audit trail.

See `docs/design/FRAMEWORK_CONTEXT.md` §3, Database Migrations for the pattern, rationale, and production exemplars.

**Phase-7-managed table exception:** `encoder_cache` is created by `create_tables_async()` at Phase 7, not by Alembic. Any migration referencing `encoder_cache` must include a `sqlite_master` existence check before operating on the table. See `docs/design/FRAMEWORK_CONTEXT.md` §3, Phase-7-Managed Tables for the required guard pattern and canonical example.

### Schema Lockstep Rule

Every Alembic migration that adds or modifies a table or column must also update **all three** of the following files in the same commit:

1. `src/stoat_ferret/db/schema.py` — `create_tables_async()` raw SQL DDL that recreates the table structure.
2. `tests/test_contract/test_repository_parity.py` — contract test asserting the new column is present and has the expected type.
3. `tests/security/test_audit.py` — SQL allowlist. Line numbers shift when columns are added; stale line numbers fail the security audit probe.

**Why three files?** `create_tables_async` is used by tests and is the authoritative schema for fresh installs; the contract test enforces parity; the allowlist is line-number-sensitive. Discovering any of these in CI requires an additional 5–10 minute run. Check all three before the first push.

---

## Structured Event Naming

### Event Namespace Rule

All structured log events (`logger.info("event_name", key=value)`) must use an approved namespace. Event names are part of the observability contract — renaming them breaks log queries, dashboards, and alerting rules.

**Approved namespaces:**

| Namespace | Category | Purpose |
|-----------|----------|---------|
| `deployment.*` | Infrastructure | Startup, migrations, feature flag recording |
| `synthetic.*` | Infrastructure | Synthetic monitoring probes |
| `schema.*` | Infrastructure | Schema consistency checks |
| `preview.*` | Domain | Preview workflow WebSocket events |
| `proxy.*` | Domain | Proxy workflow WebSocket events |
| `render.*` | Domain | Render workflow events |
| `testing.*` | Domain (gated) | Testing/debug operations (feature-gated) |
| (no namespace) | Domain background | High-volume background job lifecycle events (batch, scan, thumbnail) |

**Boundary rule:** `deployment.*` and `synthetic.*` are reserved for infrastructure events (startup, migrations, monitoring probes). Do not use `deployment.*` for domain or user-visible workflow events.

**No-namespace rule:** Background job lifecycle events (batch_*, job_*, scan_*, thumbnail_*) intentionally carry no namespace prefix. This reduces log verbosity at high event rates. Log queries that filter by namespace automatically exclude this category.

**Declaration-before-use process:**
1. Propose the new namespace in the PR description.
2. Add the namespace to `docs/design/FRAMEWORK_CONTEXT.md` §3, Structured Logging & Event Naming, and merge to main.
3. Use the namespace in code only after the FRAMEWORK_CONTEXT.md update is merged.

Ad-hoc event names without an approved namespace are not permitted.

See `docs/design/FRAMEWORK_CONTEXT.md` §3, Structured Logging & Event Naming for the complete namespace taxonomy and production exemplars.

---

## PyO3 Bindings

### Incremental Binding Rule

When implementing new Rust types or functions, add PyO3 bindings in the SAME feature. Do not defer bindings to a later feature—this creates tech debt that accumulates.

**Wrong:** Implement Rust type in feature 1, add bindings in feature 5.
**Right:** Implement Rust type AND bindings together in feature 1.

### Stub Regeneration

After modifying any PyO3 bindings, regenerate type stubs:

```bash
cd rust/stoat_ferret_core
cargo run --bin stub_gen
```

> **Warning — Do NOT copy stub_gen output wholesale.** Running
> `cargo run --bin stub_gen` and copying its output file directly to
> `src/stoat_ferret_core/_core.pyi` strips all hand-written `__new__`
> constructors and produces 100+ mypy errors. Always use append-only
> edits: restore from main and add only the new classes.

CI verifies stubs match the Rust API. Forgetting to regenerate will cause CI failure.

### Naming Convention

Use `py_` prefix for Rust method names, with `#[pyo3(name = "...")]` to expose clean names to Python:

```rust
#[pymethods]
impl MyType {
    #[pyo3(name = "calculate")]
    fn py_calculate(&self, value: i32) -> i32 {
        // Implementation here
    }
}
```

This allows:
- Rust: `my_type.py_calculate(5)` (internal Rust call)
- Python: `my_type.calculate(5)` (clean API, no py_ prefix visible)

The `py_` prefix distinguishes PyO3 binding methods from pure Rust methods, making it clear which methods are part of the Python API.

### Internal Error Enums

Declare error enums as `pub(crate)` when they exist solely to propagate failure modes
within a single Rust module. A `pub(crate)` type is not reachable through PyO3; Python
callers only see the `PyValueError` mapped at the `build()` call site. No `#[gen_stub_pyclass]`
attribute, no `stub_gen` run, and no `.pyi` update are required.

Pattern: `pub(crate)` error enum → returned by `pub(crate)` helper → caught in `pub` builder
→ mapped to `PyValueError`. Python callers receive a descriptive `ValueError`; the Rust
error type is invisible.

### Enum Non-Hashability Guardrail

**PyO3 0.26 enum values are not hashable** and cannot be used directly as dict keys or set members. Use `str(enum_field)` instead:

```python
# Wrong — raises TypeError: unhashable type
key = my_enum.field        # PyO3 enum is not hashable
cache[key] = value

# Correct — convert to string first
key = str(my_enum.field)   # use str() for dict/set keying
cache[key] = value
```

This applies to all PyO3-bound enum types.

### Per-Module Coverage Gate

When a Rust type or function is **only callable through the PyO3 boundary** (no internal Rust callers), Python tests cover the PyO3 surface contract but may not drive enough Rust-internal code paths to satisfy the project's per-module coverage gate (>95%).

Fix: add a `#[cfg(test)] mod tests` block that calls constructors and validators directly from Rust.

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_reject_nan() {
        assert!(MyBuilder::py_new(f64::NAN).is_err());
    }
}
```

**Rule of thumb:** Python tests pin the PyO3 surface contract (argument passing, error types, return shapes). Rust unit tests pin Rust invariants (validation ordering, guard conditions). Both are needed when the PyO3 entry point is the only public entry to a module.

### Example: Complete Type with Bindings

```rust
use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use pyo3_stub_gen::derive::gen_stub_pyclass;

#[gen_stub_pyclass]
#[pyclass]
#[derive(Debug, Clone)]
pub struct Segment {
    #[pyo3(get)]
    pub start: u64,
    #[pyo3(get)]
    pub end: u64,
}

#[pymethods]
impl Segment {
    #[new]
    fn py_new(start: u64, end: u64) -> PyResult<Self> {
        if end <= start {
            return Err(PyValueError::new_err("end must be > start"));
        }
        Ok(Self { start, end })
    }

    #[pyo3(name = "length")]
    fn py_length(&self) -> u64 {
        self.end - self.start
    }
}
```

Always regenerate stubs after adding or modifying bindings.

---

## PR Workflow

After completing code changes, follow this workflow:

### PR Authoring Checklist

Before creating a PR, confirm each item that applies to your change:

- **API field changed?** — Did you add, rename, or remove a request/response field? If yes, run:
  ```bash
  uv run python -m scripts.export_openapi
  cd gui && npm run generate:types
  ```
- **New module added?** — Did you add a new Python module or Rust binding? If yes, update type stubs
  (`cargo run --bin stub_gen` + restore-and-append) and add any new PyO3 types to `_core.pyi`.
- **Smoke skip resolved?** — Did you fix a bug or feature referenced in an existing
  `pytest.mark.skip(reason="...")` message? If yes, remove or update the skip marker.
- **Route/model changed?** — Did you modify a FastAPI route decorator, Pydantic model, or response
  schema? If yes, regenerate `gui/openapi.json` and `gui/src/generated/api-types.ts` (same commands
  as API field changed above).

These four checks intercept the leading documentation-drift categories. See §OpenAPI Schema Sync
for the full regeneration procedure.

### 1. Verify locally
```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest
cd rust/stoat_ferret_core && cargo fmt --check && cargo clippy -- -D warnings && cargo test
```

> **Rust format! string length:** Long `format!` error strings that exceed the project's 100-character line limit cause `cargo fmt --check` failures in CI. Break them at authoring time — `cargo fmt` is free; a CI re-run costs 5–10 minutes. Run `cargo fmt --check` locally before the first push.

Fix any failures before proceeding.

### 2. Commit and push
```bash
git add -A
git commit -m "feat: <description>"
git push -u origin HEAD
```

### 3. Create PR
```bash
gh pr create --fill --base main
```

### 4. Wait for CI and handle failures
```bash
gh pr checks --watch
```

**If CI fails:**
1. View the failure: `gh run view --log-failed`
2. Fix the issues locally
3. Run local verification again (step 1)
4. Commit and push the fix
5. Wait for CI again

**Iteration limit:** Repeat the fix cycle up to **3 times maximum**. If CI still fails after 3 fix attempts:
- Document the persistent issue in your completion report
- Set status to "partial" or "failed"
- Do NOT loop indefinitely
- Return/complete the task

### 5. Merge when CI passes
```bash
gh pr merge --squash --delete-branch
```

### 6. Verify merge
```bash
git checkout main
git pull
```

---

## When Called by MCP Server

When the MCP server invokes you to implement a feature:

1. **Read the prompt carefully** — It specifies which documents to read
2. **Read ALL referenced documents** before starting implementation
3. **Follow process docs** referenced in the prompt
4. **Handle the full PR lifecycle:**
   - Implement the feature
   - Create PR
   - Wait for CI
   - Fix failures (up to 3 attempts)
   - Merge when passing
5. **Create all output documents** specified (completion-report.md, quality-gaps.md, handoff-to-next.md)
6. **Return only when:**
   - PR is merged and output docs exist, OR
   - You've documented why completion wasn't possible (status: partial/failed)

**Do not return without either merging or documenting failure.**

---

## Exploration Tasks

For `explore_project` tasks called by the MCP server:
- The server handles git commit/push automatically
- Focus on creating the requested analysis documents
- Write outputs to the specified outbox path

---

## Sequential Feature Handoffs

When a feature produces artifacts consumed by a downstream sequential feature, the executor must
complete a handoff document before the downstream feature begins. Use the handoff template
from the auto-dev-mcp templates root (accessible via `get_project_info().paths.templates_root`). Do not hardcode the path.

Required sections:
- **Files Modified** — every file created or changed, with a one-line description
- **Framework Conflicts Encountered** — any rule conflicts and their resolutions
- **Cross-Feature Ordering Constraints** — startup phases, migration parents, schema dependencies
- **Known Limitations for Dependent Features** — deferred scope, out-of-scope gaps

A handoff is complete when all four sections are filled (or explicitly stated as none) and the
document is committed to main before the downstream feature begins execution.

---

## Branch Protection

The `ci-status` job is the required check for branch protection.
This allows docs-only PRs to merge without running the full test matrix.

---

## Key Architecture Decisions

- **Non-destructive editing**: Never modify source files
- **Rust for compute**: Filter generation, timeline math, input sanitization in Rust
- **Python for orchestration**: HTTP layer, API routing, AI discoverability
- **PyO3 bindings**: `from stoat_ferret_core import StoatFerretCore`
- **Transparency**: API responses include generated FFmpeg filter strings

## FFmpeg Production Role

FFmpeg is classified as **non-critical** for production readiness. The render and preview services
handle FFmpeg absence gracefully (render reports `status: "unavailable"`, preview is independent of
FFmpeg entirely). The `/health/ready` endpoint returns HTTP 200 with `status: "degraded"` when
FFmpeg is unavailable — not HTTP 503. This allows flexible deployment architectures (CPU-only
containers, remote FFmpeg, staged rollouts).

The Dockerfile runtime stage intentionally omits FFmpeg. Operators who require FFmpeg for render
must install it in a custom layer or use a sidecar pattern.

`deploy_smoke.sh` polls `/health/ready` (HTTP 200 is success regardless of degraded status).
Docker Compose uses `/health/live` for container healthchecks (faster, no subsystem probes).

## Design Documents

Authoritative design specs in `docs/design/`:

- 01-roadmap.md - Implementation phases
- 02-architecture.md - System architecture
- 03-prototype-design.md - MVP specification
- 04-technical-stack.md - Technology choices
- 05-api-specification.md - REST API design
- 06-risk-assessment.md - Risk analysis
- 07-quality-architecture.md - Quality attributes
- 08-gui-architecture.md - Web GUI design
