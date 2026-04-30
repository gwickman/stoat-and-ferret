# Phase 6 Security Review

**Scope:** Python API surface, configuration, and FastAPI endpoint group
audit for the Phase 6 production posture (scan, project, clip, timeline,
render, preview, proxy, seed, system/state, flags, schema). Conducted as
part of v043 ahead of GUI enhancement phases (v044–v045).

**Author:** v043 / theme `security-audit` / feature `001-python-security-audit`
**Backlog item:** BL-286
**Rust audit:** appended below as §10 (BL-287, same theme — parallel feature).
**Probe suite:** `tests/security/test_audit.py` (12 probes, 11 active +
1 platform-skipped on Windows; runs in <1s on CI hardware — well under
the NFR-003 30s budget).

---

## 1. Executive Summary

| Severity | Count | Notes |
|----------|------:|-------|
| **P0 (critical)** | 0 | No SQL injection, command injection, or unauthenticated privileged-action paths found. |
| **P1 (high)** | 0 | All known sensitive endpoints (`/api/v1/testing/seed`, `/api/v1/videos/scan`, render preview) have working access-control gates. |
| **P2 (medium)** | 1 | Configuration drift: 13 `STOAT_*` env vars present in `Settings` are not yet referenced anywhere under `docs/manual/`. Operator-facing risk only (no exploit). |
| **P3 (low / safe-note)** | 6 | Five intentional `f"..."` SQL identifiers (DDL / IN-clause expansion) — safe by construction; documented as allowlisted patterns. One scan-route schema note (null-byte rejection happens at the handler, not at Pydantic). |

No P0/P1 findings means this audit does not block v044/v045 GUI work.
The single P2 finding is documentation drift that should be folded into
the next manual-maintenance pass; it does not require an immediate fix
release.

---

## 2. Methodology

The audit combined three techniques:

1. **AST-walking probe** over `src/stoat_ferret/` for any
   `.execute()` / `.executemany()` / `.executescript()` invocation whose
   first argument is an f-string or `%`-formatted string containing an
   SQL keyword. Findings are compared against an explicit allowlist of
   known-safe DDL / IN-clause patterns; anything outside the allowlist
   fails the probe (`test_no_sql_fstring_interpolation`,
   `test_sql_interpolation_allowlist_is_live`).
2. **Live HTTP probes** against a `TestClient`-driven `create_app`
   instance. The seed endpoint is exercised with `STOAT_TESTING_MODE`
   off (default) to verify the 403 guard, and again with the flag on to
   confirm the `seeded_` prefix is enforced. The scan endpoint is
   probed with null-byte, double-encoded, relative `../`, and
   outside-allowed-root payloads.
3. **Configuration inventory** — Pydantic `Settings` model fields are
   enumerated programmatically and cross-referenced against every
   `STOAT_*` reference under `docs/manual/`. Any var that is not yet
   documented and not on the explicit drift baseline fails the probe.

Tests run as part of the standard CI pytest matrix (Python 3.10–3.12 ×
Linux/macOS/Windows). No external network or live database is required.

---

## 3. Endpoint Coverage Matrix (NFR-001)

Every documented Phase 6 endpoint group is covered by at least one
probe — directly via the new `test_audit.py` suite or transitively via
existing security tests in `tests/test_security/`.

| Endpoint Group | Probe Coverage |
|----------------|----------------|
| `POST /api/v1/videos/scan` | `test_path_traversal_null_byte_rejected`, `test_path_traversal_double_encoded_rejected`, `test_path_traversal_relative_dotdot_rejected`, `test_path_outside_allowed_root_returns_403`, `test_path_traversal_symlink_escape_blocked` (skipped on Windows). |
| `GET/POST /api/v1/projects` | SQL injection probe covers `project_repository.py` (parameterised queries verified). |
| `GET/PATCH/DELETE /api/v1/projects/{id}/clips` | SQL injection probe covers `clip_repository.py`. |
| `GET/PUT /api/v1/projects/{id}/timeline` | SQL injection probe covers `timeline_repository.py`. |
| `POST /api/v1/render`, `POST /api/v1/render/{id}/cancel`, `GET /api/v1/render/queue` | SQL injection probe covers `render_repository.py`, `checkpoints.py`. IN-clause expansion in `cleanup_stale` is allowlisted (see §5.1). |
| `POST /api/v1/render/preview`, `POST /api/v1/effects/preview` | SQL injection probe covers `preview_repository.py`; existing `tests/test_security/test_input_sanitization.py` validates filter-text and codec whitelist enforcement (BL-085). |
| `GET/DELETE /api/v1/videos/{id}/proxy` | SQL injection probe covers `proxy_repository.py`. |
| `POST /api/v1/testing/seed`, `DELETE /api/v1/testing/seed/{id}` | `test_seed_endpoint_blocked_without_testing_mode`, `test_seed_delete_blocked_without_testing_mode`, `test_seeded_prefix_enforcement_when_testing_mode_enabled`. |
| `GET /api/v1/system/state` | Read-only state surface; covered transitively by config drift audit and existing `test_synthetic_monitoring.py`. |
| `GET /api/v1/flags` | Read-only flag projection; covered by existing `tests/test_flags.py`. |
| `GET /api/v1/schema/...` | Schema introspection only; no user-driven input reaches SQL or filesystem. |

---

## 4. Findings

### 4.1. P2-CONFIG-001 — `STOAT_*` env vars missing from manual

**Status:** RESOLVED in v045 with Feature 002 (operator-security-configuration-guide).
The 13 audit-baseline variables are now documented in
`docs/manual/configuration-reference.md` with operator and security
context, and `KNOWN_UNDOCUMENTED_SETTINGS_VARS` in
`tests/security/test_audit.py` has been shrunk to an empty
`frozenset()`. Both drift probes pass.

**Severity:** P2 (medium — operator/documentation risk; no security
exploit, no data exposure).

**Description:** The Pydantic `Settings` model in
`src/stoat_ferret/api/settings.py` defines 41 `STOAT_*` environment
variables. 13 of these are not yet referenced in any file under
`docs/manual/`. Operators cannot tune them without reading the source.

The probe `test_settings_env_vars_documented_or_known_drift` enforces
this list as the current drift baseline; any *new* undocumented var
introduced after this audit causes the probe to fail. The companion
`test_known_drift_baseline_still_undocumented` removes pressure on the
allowlist by failing when an entry has been resolved (so the baseline
shrinks naturally as the manual catches up).

**Drift baseline (13 vars):**

```
STOAT_BATCH_MAX_JOBS
STOAT_BATCH_RENDERING
STOAT_PREVIEW_CACHE_MAX_BYTES
STOAT_PREVIEW_CACHE_MAX_SESSIONS
STOAT_PREVIEW_SEGMENT_DURATION
STOAT_PREVIEW_SESSION_TTL_SECONDS
STOAT_PROXY_AUTO_GENERATE
STOAT_PROXY_CLEANUP_THRESHOLD
STOAT_SEED_ENDPOINT
STOAT_SYNTHETIC_MONITORING
STOAT_SYNTHETIC_MONITORING_INTERVAL_SECONDS
STOAT_THUMBNAIL_STRIP_INTERVAL
STOAT_VERSION_RETENTION_COUNT
```

**Recommendation:** Addressed in v045. The 13 drift-baseline variables
are now documented in `docs/manual/configuration-reference.md` with
operational and security context, and the canonical setup reference at
`docs/setup/04_configuration.md` covers all 41 `STOAT_*` variables.
Going forward, the process rule in `AGENTS.md § Documentation
Standards` requires both setup and manual entries (and an empty drift
baseline) for any new `STOAT_*` variable; the probe enforces "no new
drift" automatically.

**Tracking:** Closed under v045 Feature 002 (BL-317). The probe's drift
baseline is now empty; new undocumented variables will fail
`test_settings_env_vars_documented_or_known_drift` immediately.

---

## 5. Allowlisted (Safe by Construction) Patterns

These were detected by the AST probe and verified by code review; each
is documented as a P3 safe-note rather than a finding because the
interpolated values are not user-controllable.

### 5.1. P3 — `f"..."` SQL identifiers in DDL / IN-clause expansion

**Affected sites (6 — all allowlisted):**

| Location | Pattern | Why it is safe |
|----------|---------|----------------|
| `src/stoat_ferret/db/schema.py:343` | `conn.execute(f"ALTER TABLE projects ADD COLUMN {col} {col_type}")` | `(col, col_type)` come from the constant `PROJECTS_AUDIO_MIX_COLUMNS` list — no user input. |
| `src/stoat_ferret/db/schema.py:359` | `conn.execute(f"ALTER TABLE clips ADD COLUMN {col} {col_type}")` | Same: values from the constant `CLIPS_TIMELINE_COLUMNS` list. |
| `src/stoat_ferret/db/schema.py:425` | `await db.execute(f"ALTER TABLE projects ADD COLUMN {col} {col_type}")` | Async equivalent of the line-343 helper, same constants. |
| `src/stoat_ferret/db/schema.py:441` | `await db.execute(f"ALTER TABLE clips ADD COLUMN {col} {col_type}")` | Async equivalent of the line-359 helper, same constants. |
| `src/stoat_ferret/api/services/migrations.py:428` | `conn.execute(f"PRAGMA table_info({table_name})")` | `table_name` comes from a prior `SELECT name FROM sqlite_master` query — only existing user tables, no client input. |
| `src/stoat_ferret/render/checkpoints.py:140` | `await self._conn.execute(f"DELETE FROM render_checkpoints WHERE job_id IN ({placeholders})", job_ids)` | `placeholders = ",".join("?" for _ in job_ids)` — produces only `?` and `,`. The actual job ids are bound through the second argument. Canonical IN-clause expansion pattern. |

**Why this is the right approach:** SQLite (and most relational
databases) does not support parameter binding for identifiers (table
names, column names) or for the *number* of placeholders in an IN
clause. F-string interpolation is the only available mechanism for
these specific patterns. Code review confirmed that no user-controllable
data reaches any of the six interpolation points.

**Detection:** all six lines are encoded in
`SQL_INTERPOLATION_ALLOWLIST` in `tests/security/test_audit.py`.
`test_sql_interpolation_allowlist_is_live` ensures the allowlist stays
synchronised with the source: a refactor that moves any of these calls
must update the allowlist or the probe fails.

### 5.2. P3 — `ScanRequest.path` schema accepts any string

**Severity:** P3 (safe-note — defence-in-depth).

The `ScanRequest` Pydantic model declares `path: str` with no
validators. Null-byte rejection happens later, at the
`os.path.isdir()` call inside the route handler — `os.path.isdir`
returns `False` (rather than raising) on Windows, and the route then
emits a 400 `INVALID_PATH` response. On Linux/macOS the behaviour is
the same in practice because `os.path.isdir` returns `False` for the
synthetic null-byte path.

**Verified behaviour (probes pass):** all four traversal payloads —
null-byte, double-encoded, relative `../`, outside-allowed-root —
return 4xx responses, and the symlink-escape probe (Linux/macOS only)
returns 403. No payload reached the handler with a 2xx status.

**Recommendation (optional, not a fix-required finding):** Consider
adding a `field_validator("path")` on `ScanRequest` that rejects null
bytes at schema time so the rejection is encoded at the API contract
rather than relying on transitive `os.path.isdir` behaviour. This is a
hygiene improvement, not a security gap — the audit confirmed all
exploitation attempts are already blocked.

---

## 6. Verified Defences (No Action Required)

| Defence | Evidence |
|---------|----------|
| All repository CRUD uses `?` placeholders for values | `git grep "execute("` across `src/stoat_ferret/db/` shows the value-binding pattern at every call site; the AST probe enforces this. |
| `POST /api/v1/testing/seed` returns 403 when `STOAT_TESTING_MODE` is off | `test_seed_endpoint_blocked_without_testing_mode` (active probe). |
| `DELETE /api/v1/testing/seed/{id}` enforces the same gate | `test_seed_delete_blocked_without_testing_mode`. |
| Seed fixtures are forced under the `seeded_` prefix | `test_seeded_prefix_enforcement_when_testing_mode_enabled` (INV-SEED-2). |
| Path traversal (null byte / `..` / double-encoded) is rejected before scan starts | Three new probes + four existing probes in `tests/test_security/test_path_validation.py`. |
| `allowed_scan_roots` enforcement resolves symlinks before checking | `test_path_traversal_symlink_escape_blocked` (Linux/macOS) + existing `test_symlink_resolved_against_root`. |
| FFmpeg filter strings escape user input | Existing `tests/test_security/test_input_sanitization.py` (DrawtextBuilder, escape_filter_text, validate_path, codec/preset whitelists). Confirmed by code review of `src/stoat_ferret/effects/` — no shell invocation, only filter-graph string construction. |
| Render preview and effects preview endpoints validate codec / preset / format inputs against whitelists in the Rust core | Existing probes in `test_input_sanitization.py::TestWhitelistBypass`. |

---

## 7. Cross-Reference to Companion Audits

- **BL-287 (Rust dependency audit)** covers Rust `unsafe`, panic paths,
  FFmpeg command construction, and CVE scanning via `cargo audit` and
  `pip-audit`. Findings appended in §10 below.
- **BL-288 (load / performance)** is a separate feature; out of scope.

---

## 8. Open Backlog Items Filed

Per the Risk 5 mitigation in `THEME_DESIGN.md`, P0/P1 findings would be
filed as separate backlog items so this audit could ship fast.

**This audit identified zero P0 and zero P1 findings.** No new backlog
items are filed. The single P2 (config drift) is encoded in the probe's
baseline list and tracked there until the manual catches up.

---

## §9 Audit Cadence

The security audit cadence is now formalized in `docs/security/audit-cadence.md`. See that document for triggers, scope, deliverables, and review schedule.

---

**Audit complete.** No fixes required for v043 to ship; the single P2
config-drift finding is documentation hygiene tracked by the probe
baseline.

---

## 10. Rust Core Audit (BL-287)

**Author:** v043 / theme `security-audit` / feature `002-rust-dependency-audit`
**Backlog item:** BL-287
**Crate:** `stoat_ferret_core` (Rust core; PyO3 bindings to Python)
**Companion artifact:** `UNSAFE_BLOCK_INVENTORY.md` (project root).

### 10.1. Executive Summary

| Severity | Count | Notes |
|----------|------:|-------|
| **P0 (critical)** | 0 | No exploitable unsafe blocks, no panic paths reachable through normal Python API usage, no shell-based FFmpeg invocation. |
| **P1 (high)** | 0 | All `cargo audit` warnings scope to build-time / test-only crates; `pip-audit` finding is non-exploitable in this codebase. |
| **P2 (medium)** | 0 | No medium-severity production exposure identified. |
| **P3 (low / safe-note)** | 4 | (1) `python-dotenv` 1.2.1 transitive CVE — not exploitable here. (2) `cargo audit` unmaintained-crate warnings via `pyo3-stub-gen`. (3) `expect()` calls in `DuckingPattern.build()` and `AudioMixSpec.build()` — panic-safe by construction. (4) `expect()` in `stub_info()` build-only helper. |

No P0/P1 findings. The Rust core is structurally panic-safe through
Python API usage; the few `expect()` calls in production paths each
encode a static or pre-validated invariant.

### 10.2. Methodology

1. **Unsafe block scan** — `grep -rn 'unsafe[ {]'` across
   `rust/stoat_ferret_core/src/` and the broader `rust/` tree. See
   `UNSAFE_BLOCK_INVENTORY.md` for the inventory.
2. **Panic-path review** — every `#[pymethods]` impl block was inspected
   for `unwrap()`, `expect()`, `panic!()`, `unreachable!()`,
   `todo!()`, and `unimplemented!()`. Doc comments and `#[cfg(test)]`
   modules were excluded; the residual production-code matches were
   read in context to verify each is panic-safe by construction.
3. **FFmpeg sanitization review** — `grep` for `std::process::Command`,
   `Command::new`, `sh -c`, and shell-pipe patterns; cross-referenced
   against `sanitize::escape_filter_text`, `sanitize::validate_path`,
   and the codec/preset whitelists in `sanitize/mod.rs`.
4. **Cargo audit** — `cargo audit` run fresh on `Cargo.lock` (166
   crate dependencies, advisory DB 1058 advisories).
5. **Pip-audit** — `uv export --no-dev --format requirements-txt` →
   `pip-audit -r ...` against the resolved runtime dependency list (no
   dev tools).

### 10.3. Findings

#### 10.3.1. P3-RUST-DOTENV — `python-dotenv` 1.2.1 transitive CVE-2026-28684

> **✓ Resolved in v048** — `python-dotenv>=1.2.2` added to `pyproject.toml` [project].dependencies; uv.lock now pins 1.2.2. See BL-318.

**Severity:** P3 (low — vulnerability advisory exists but exploitation
preconditions are absent in this codebase).

**Description:** `pip-audit` reports CVE-2026-28684 (GHSA-mf9w-mj56-hr94)
against `python-dotenv` 1.2.1 (transitive dep via `pydantic-settings`
and `uvicorn[standard]`). The advisory describes a TOCTOU symlink-
following bug in `set_key()` / `unset_key()` when `/tmp` and the target
.env directory are on different filesystems — these helpers fall back
to `shutil.copy2()` (which follows symlinks) on cross-device rename
failure, allowing a local attacker who can pre-place a symlink to
cause the application to overwrite an arbitrary file with `.env`-
formatted content.

**Why it is not exploitable here:**

```
$ grep -rn 'set_key\|unset_key\|from dotenv\|import dotenv' src/ tests/
# → no matches
```

`pydantic-settings` only *reads* environment variables (and at most
parses a `.env` file via `load_dotenv()` semantics); the project never
calls `set_key()` or `unset_key()`, the only entry points the CVE
applies to. `python-dotenv` is also pulled in by `uvicorn[standard]`
for `--env-file` support but, again, only for reading.

**Fix versions:** 1.2.2.

**Recommendation:** Bump `python-dotenv` to 1.2.2 the next time the
lockfile is refreshed (no rush — the codebase does not exercise the
vulnerable code path). Tracked as a soft dependency-hygiene follow-up;
no separate backlog item filed because the CVE is non-exploitable
here.

#### 10.3.2. P3-RUST-CARGO-UNMAINTAINED — Build/test-only unmaintained-crate warnings

**Severity:** P3 (low — warnings only, no CVE; advisories scoped to
crates that do not ship in the runtime artifact).

**Description:** `cargo audit` reports 8 advisory warnings, all of
which trace back to `pyo3-stub-gen` (used at build time only, by
`cargo run --bin stub_gen`) or `proptest` (test-only `[dev-dependencies]`).
None reach the runtime PyO3 module that ships with the Python wheel.

| Advisory | Crate | Origin | Reason | Runtime impact |
|----------|-------|--------|--------|----------------|
| RUSTSEC-2025-0075 | `unic-char-range` | `pyo3-stub-gen-derive` → `rustpython-parser` | unmaintained | none (build-only) |
| RUSTSEC-2025-0080 | `unic-common` | `pyo3-stub-gen-derive` | unmaintained | none (build-only) |
| RUSTSEC-2025-0081 | `unic-char-property` | `pyo3-stub-gen-derive` | unmaintained | none (build-only) |
| RUSTSEC-2025-0090 | `unic-emoji-char` | `pyo3-stub-gen-derive` | unmaintained | none (build-only) |
| RUSTSEC-2025-0098 | `unic-ucd-version` | `pyo3-stub-gen-derive` | unmaintained | none (build-only) |
| RUSTSEC-2025-0100 | `unic-ucd-ident` | `pyo3-stub-gen-derive` | unmaintained | none (build-only) |
| RUSTSEC-2026-0097 | `rand` 0.8.5 | `pyo3-stub-gen-derive` → `unicode_names2` | unsound (custom logger) | none (build-only) |
| RUSTSEC-2026-0097 | `rand` 0.9.2 | `proptest` | unsound (custom logger) | none (test-only) |

**Why none are P1 or P2:** all eight advisories are unmaintained-crate
or unsoundness warnings, none are CVE-classified vulnerabilities
(CVSS scores are not assigned). The `unic-*` chain is pulled in only
by `pyo3-stub-gen-derive`, which is exercised by the `stub_gen` binary
during local development (regenerating `.generated-stubs/`); it is not
linked into the PyO3 cdylib that ships in the Python wheel. The two
`rand` advisories require a custom logger configuration that the
project does not install.

**Recommendation:** monitor for an upstream `pyo3-stub-gen` release
that drops the `rustpython-parser` dependency tree; otherwise no
action is required for v043 — the crate auditor's
"warning: 8 allowed warnings found" exit code is **0** so CI is not
blocked.

#### 10.3.3. P3-RUST-EXPECT — `expect()` calls in PyO3-reachable production code

**Severity:** P3 (safe-note — each call is panic-safe by construction;
the `.expect()` message documents the invariant).

**Description:** Three production functions reachable through
`#[pymethods]` use `.expect()` rather than `?`/`PyResult` propagation.
Code review confirmed every one is panic-safe by static or
pre-validated invariant; none can be triggered by user input through
the Python API.

| File:Line | Call site | Reachable from Python via | Why panic-safe |
|-----------|-----------|---------------------------|----------------|
| `ffmpeg/audio.rs:723` | `graph.compose_branch("0:a", 2, true).expect("compose_branch with count=2 cannot fail")` | `DuckingPattern.build()` | `count = 2` is a hardcoded literal; `compose_branch` only fails when `count == 0`. |
| `ffmpeg/audio.rs:734` | `graph.compose_merge(&[branches[0], branches[1]], sc_filter).expect("compose_merge with 2 inputs cannot fail")` | `DuckingPattern.build()` | `branches` has length 2 (asserted by line 721 `count=2`); `compose_merge` only fails when input slice is empty. |
| `ffmpeg/audio.rs:741` | `graph.compose_chain(&compressed, vec![Filter::new("anull")]).expect("compose_chain with one filter cannot fail")` | `DuckingPattern.build()` | The filter Vec is constructed inline with one element. |
| `ffmpeg/audio.rs:1017` | `VolumeBuilder::new(track.volume).expect("volume pre-validated in TrackAudioConfig")` | `AudioMixSpec.build()` | `track.volume` is bounds-checked to `[0.0, 2.0]` in `TrackAudioConfig::new`, which is the only constructor path. |
| `ffmpeg/audio.rs:1024` | `AfadeBuilder::new("in", track.fade_in).expect("fade_in pre-validated as > 0")` | `AudioMixSpec.build()` | Guarded by `if track.fade_in > 0.0` immediately above. |
| `ffmpeg/audio.rs:1031` | `AfadeBuilder::new("out", track.fade_out).expect("fade_out pre-validated as > 0")` | `AudioMixSpec.build()` | Guarded by `if track.fade_out > 0.0` immediately above. |
| `ffmpeg/audio.rs:1045` | `AmixBuilder::new(self.tracks.len()).expect("track count pre-validated in range [2, 8]")` | `AudioMixSpec.build()` | `tracks` length is bounds-checked to `[2, 8]` in `AudioMixSpec::new`. |
| `render/encoder.rs:16` | `Regex::new(r"^\s([VAS][F.][S.][X.][B.][D.])\s(\S+)\s+(.+?)(?:\s+\(codec (\S+)\))?$").unwrap()` | `parse_encoder_list()` (PyO3-exposed) | Static literal regex inside `LazyLock`; compilation never fails for a valid pattern. |
| `render/encoder.rs:169,174,175` | `caps.get(1/2/3).unwrap().as_str()` | `parse_encoder_list()` | Inside the `if let Some(caps) = ENCODER_RE.captures(line)` arm; groups 1–3 are non-optional in the regex pattern (no `?` quantifier). |
| `timeline/range.rs:121` | `Duration::between(self.start, self.end).unwrap()` | `TimeRange.duration()` | Comment on the line: "Safe to unwrap: we guarantee end > start in the constructor." `TimeRange::new` rejects `end <= start` with a `Result::Err`. |
| `timeline/range.rs:499` | `merged.last_mut().unwrap()` | `merge_ranges()` (free fn, exposed via PyO3 wrapper) | Inside `for range in &sorted[1..]`; `merged` is initialized with `vec![sorted[0]]` on line 497 and only grows from there — never empty. |

**Recommendation:** these call sites are correct and idiomatic. A
strict-ifing pass could replace `expect()` with `if let`/`?` to
shorten the trust chain, but that is a code-style improvement, not a
security fix. No backlog item is filed.

#### 10.3.4. P3-RUST-STUB-INFO — `expect()` in build-only `stub_info()` helper

**Severity:** P3 (safe-note — build-time only, not part of any
Python-callable path).

**Description:** `lib.rs:172-176` uses `.expect()` to traverse from
`CARGO_MANIFEST_DIR` up two levels to find the project root for stub
generation:

```rust
let project_root = manifest_dir
    .parent()
    .expect("Failed to get rust/ directory")
    .parent()
    .expect("Failed to get project root");
```

This function (`stub_info()`) is invoked exclusively by the `stub_gen`
binary (`cargo run --bin stub_gen`), which runs at developer time to
regenerate `.generated-stubs/`. The crate ships with the panicking
function compiled in (it is `pub`), but it is not registered via
`#[pyfunction]` or `m.add_function(...)` in the `_core` module init,
so Python cannot call it.

**Recommendation:** none. The two unwraps would only fail on a
malformed source layout (e.g., `rust/stoat_ferret_core/Cargo.toml`
moved to the workspace root) — a `cargo run --bin stub_gen` failure
in that scenario is the desired behaviour.

### 10.4. Verified Defences (No Action Required)

| Defence | Evidence |
|---------|----------|
| Zero `unsafe` blocks in the crate | `UNSAFE_BLOCK_INVENTORY.md`; grep returns no matches across `rust/stoat_ferret_core/src/`. |
| Rust never invokes a shell or executes FFmpeg directly | `grep -rn 'std::process::Command\|sh -c'` shows all matches are doc-comments or test-only references; the crate produces `Vec<String>` argument arrays for the Python layer to pass to `subprocess`. |
| All `#[pymethods]` constructors return `PyResult<T>` and surface bounds errors as `PyValueError` | Code review of each `#[new]` and `#[pyo3(name = ...)]` method (e.g., `DuckingPattern::py_threshold`, `TrackAudioConfig::py_new`, `AfadeBuilder::py_new`). |
| Filter text injection blocked by `escape_filter_text` | `sanitize/mod.rs` escapes `\`, `'`, `:`, `[`, `]`, `;`, `\n`, `\r`. Existing `tests/test_security/test_input_sanitization.py` exercises adversarial payloads. |
| Drawtext-specific format-string injection blocked | `ffmpeg/drawtext.rs:32` extends `escape_filter_text` with `%` → `%%`. |
| Path null-byte / empty-string injection blocked at the Rust boundary | `sanitize::validate_path` rejects empty strings and any `\0` byte; `py_validate_path` is registered on the `_core` module. |
| Codec / preset injection blocked by whitelist | `sanitize::VIDEO_CODECS`, `AUDIO_CODECS`, `PRESETS` constants enumerate the allowed values; everything else returns `BoundsError::InvalidValue` → `PyValueError`. |
| Numeric parameter ranges enforced before reaching FFmpeg | `validate_crf` (0–51), `validate_speed` (0.25–4.0), `validate_volume` (0.0–10.0), and per-builder bounds checks on threshold/ratio/attack/release in `DuckingPattern`. |
| Phase 6 modules (`schema.rs`, `version.rs`) panic-safe | All `#[pymethods]` on `ParameterSchema`, `Version`, `VersionMetadata` use `PyResult<T>` and `?`; no `unwrap()` outside `#[cfg(test)]`. |

### 10.5. Tool Output Excerpts

#### `cargo audit` (run 2026-04-27)

```
    Fetching advisory database from `https://github.com/RustSec/advisory-db.git`
      Loaded 1058 security advisories (from C:\Users\grant\.cargo\advisory-db)
    Updating crates.io index
    Scanning Cargo.lock for vulnerabilities (166 crate dependencies)
…
warning: 8 allowed warnings found
```

Exit code 0; all 8 warnings are unmaintained / unsound advisories on
build-time or test-only dependencies (see §10.3.2 table).

#### `pip-audit -r <uv export>` (run 2026-04-27)

```
Found 1 known vulnerability in 1 package
Name          Version ID             Fix Versions
------------- ------- -------------- ------------
python-dotenv 1.2.1   CVE-2026-28684 1.2.2
```

See §10.3.1 for non-exploitability analysis.

### 10.6. Re-Audit Cadence

- **Per release (lightweight):** `cargo clippy -- -D warnings` and
  `cargo test` already run in CI; if `cargo-audit` is added to CI in a
  future release, the dependency advisories will surface automatically.
- **Per Phase / quarterly (full):** repeat this manual review (panic-
  path scan, cargo audit, pip-audit, FFmpeg sanitizer review) before
  the next major capability phase or six months from now, whichever
  comes first.
- **Trigger immediate re-audit if:** any new `unsafe` block is
  introduced, any new external Rust crate is added to `Cargo.toml`, or
  PyO3 is upgraded to a major new version.

### 10.7. Open Backlog Items Filed

Per Risk 5 mitigation, P0/P1 findings would be filed as separate
backlog items so this audit could ship fast.

**This audit identified zero P0 and zero P1 findings.** No new backlog
items are filed. The four P3 safe-notes are documented inline above
and require no follow-up beyond the dependency-hygiene `python-dotenv`
bump on the next lockfile refresh.

---

**Rust audit complete.** No fixes required for v043 to ship; the four
P3 safe-notes are non-exploitable in the current codebase.
