# Task 001: Discovery and Planning

Read AGENTS.md first and follow all instructions there.

## Objective

Discover all code directories in the project, determine which need processing (full or delta), and produce a directory manifest with batch groupings for parallel code-level analysis.

## Context

This is the first step in C4 architecture documentation generation for `${PROJECT}` version `${VERSION}`.
- **Mode:** `${MODE}` (full = all directories; delta = only changed since `${PREVIOUS_VERSION}`)
- **Previous C4 commit:** `${PREVIOUS_C4_COMMIT}` (git SHA; empty if MODE is full)
- If mode is `delta`, only directories containing files changed since `${PREVIOUS_C4_COMMIT}` will be processed.

## Tasks

### 1. Discover All Source Directories

Walk the project tree and collect all directories that contain source code files. Apply these exclusion filters:

**Exclude directories matching:**
- `node_modules`, `.git`, `build`, `dist`, `__pycache__`, `.tox`, `.mypy_cache`, `.pytest_cache`
- `.venv`, `venv`, `env`, `.env`, `.eggs`, `*.egg-info`
- `C4-Documentation`, `comms/`, `docs/auto-dev/`, `docs/ideation/`
- Any directory that contains ONLY non-code files (markdown, config, etc.)

**Include directories that contain:**
- `.py`, `.ts`, `.js`, `.tsx`, `.jsx`, `.go`, `.rs`, `.java`, `.cs`, `.rb` files
- Other recognized source code files

Sort discovered directories by depth (deepest first) for bottom-up processing.

### 2. Delta Mode: Identify Changed Directories

**If MODE is `delta`:**

Use git to find files changed since the previous C4 generation:

```bash
# Get changed files since the previous C4 commit (SHA provided by master prompt)
git diff --name-only ${PREVIOUS_C4_COMMIT} HEAD -- src/ tests/ lib/
```

Map changed files to their parent directories. Only these directories (and their ancestors up to the source root) need reprocessing.

**If MODE is `full`:** Skip this step. All directories will be processed.

### 3. Check Existing C4 Code-Level Docs

If `docs/C4-Documentation/` exists, list all existing `c4-code-*.md` files. In delta mode, these existing docs are preserved for unchanged directories.

### 4. Create Batch Groupings

Group directories into batches for parallel processing:

**Batch sizing rules:**
- Target **8-12 directories per batch** (balances parallelism vs overhead)
- Keep directories from the same parent together when possible (shared context helps the analysis)
- Maximum **6 batches** (more than this risks overwhelming the exploration queue)
- If total directories < 10, use a single batch

**For delta mode:** If fewer than 5 changed directories, use a single batch.

### 5. Produce Directory Manifest

Create the manifest that the master prompt will use to launch code-level batches.

## Output Requirements

Save outputs to `comms/outbox/exploration/c4-${VERSION}-001-discovery/`:

### README.md (required)

First paragraph: Summary of discovery results — mode, directory count, batch count.

Then:
- **Mode:** full or delta
- **Total Source Directories Found:** count
- **Directories to Process:** count (same as total for full; subset for delta)
- **Directories Unchanged (delta only):** count
- **Batch Count:** N
- **Exclusions Applied:** list of excluded patterns that matched

### directory-manifest.md (required)

Structured manifest for the master prompt to consume:

```markdown
# C4 Directory Manifest

## Metadata
- Mode: full|delta
- Total Directories: N
- Directories to Process: N
- Batch Count: N
- Previous Version: ${PREVIOUS_VERSION} (or N/A)
- Generated: YYYY-MM-DD HH:MM UTC

## Batch 1
- src/handlers
- src/handlers/auth
- src/handlers/api

## Batch 2
- src/services
- src/services/notification
- src/models

## Batch N
...

## Unchanged Directories (delta mode only)
- src/utils (existing: c4-code-src-utils.md)
- src/config (existing: c4-code-src-config.md)

## Changed Files (delta mode only)
- src/handlers/auth/login.py (modified)
- src/services/notification/email.py (added)
- tests/test_auth.py (modified)
```

### exclusion-log.md

List of all directories found and whether they were included or excluded, with reason.

## Allowed MCP Tools

- `read_document` (file creation uses Claude Code's native file system capabilities)
- `git_read`

## Guidelines

- Keep documents focused and under 200 lines each
- The manifest format must be machine-parseable by the master prompt
- In delta mode, be conservative — if unsure whether a directory changed, include it
- Do NOT create any C4 documentation in this task — discovery only
- Do NOT commit — the master prompt handles commits
