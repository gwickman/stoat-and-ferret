# AGENTS.md - stoat-and-ferret

AI-driven video editor with hybrid Python/Rust architecture.

## Project Structure

```
stoat-and-ferret/
├── src/                    # Python source (FastAPI, orchestration)
├── rust/stoat_ferret_core/ # Rust crate (filters, timeline math, FFmpeg)
├── stubs/                  # Python type stubs for Rust bindings
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

# Rust
cd rust/stoat_ferret_core
cargo clippy -- -D warnings  # Lint
cargo test                   # Test
maturin develop              # Build Python extension
```

## Quality Gates

### Python (ruff, mypy, pytest)

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

### Rust (clippy, cargo test)

```bash
cd rust/stoat_ferret_core
cargo clippy -- -D warnings
cargo test
```

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
