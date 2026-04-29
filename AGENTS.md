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
├── docs/auto-dev/          # Auto-dev process documentation
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

# Rust
cd rust/stoat_ferret_core
cargo clippy -- -D warnings  # Lint
cargo test                   # Test
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

## Type Stubs

Python type stubs for the Rust PyO3 bindings are maintained in `src/stoat_ferret_core/` (the `_core.pyi` file lives alongside the Python package).

**Manual vs Generated Stubs**: The stubs are manually maintained because `pyo3-stub-gen` generates incomplete stubs (class docstrings only, no method signatures). The generated stubs serve as a baseline for detecting new types added to Rust.

### Workflow After Modifying Rust API

1. Run stub generation:
   ```bash
   cd rust/stoat_ferret_core
   cargo run --bin stub_gen
   ```

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
```

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
```

Run this command any time you add, remove, or modify an API endpoint, Pydantic request/response model, or route decorator. Forgetting to regenerate is the most common cause of CI failures across versions.

### Coverage Thresholds

- Python: 80% minimum
- Rust: 90% minimum

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

### 1. Verify locally
```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest
cd rust/stoat_ferret_core && cargo clippy -- -D warnings && cargo test
```

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
complete a handoff document before the downstream feature begins. Use the template at
`docs/auto-dev/handoff-template.md`.

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
