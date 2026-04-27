# Phase 6 Security Review

**Scope:** Python API surface, configuration, and FastAPI endpoint group
audit for the Phase 6 production posture (scan, project, clip, timeline,
render, preview, proxy, seed, system/state, flags, schema). Conducted as
part of v043 ahead of GUI enhancement phases (v044–v045).

**Author:** v043 / theme `security-audit` / feature `001-python-security-audit`
**Backlog item:** BL-286
**Companion audit:** `docs/security/review-phase6-rust.md` (BL-287, parallel feature).
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

**Recommendation:** Treat as a documentation-only follow-up. The next
operator-guide / manual maintenance pass should either:

1. Add a settings reference section that enumerates each `STOAT_*` var,
   default value, and operator-relevant guidance; or
2. Mark vars as "internal/experimental" if they are not intended to be
   set by operators (e.g., `STOAT_SEED_ENDPOINT`, which overlaps with
   `STOAT_TESTING_MODE`).

**Tracking:** No separate backlog item required — fold into the next
manual-curation theme. The probe's drift baseline is the single source
of truth for the open list.

**Backlog cross-reference:** add a `BL-XXX` follow-up if/when the manual
team commits to a fix window. Until then, the probe enforces "no new
drift" automatically.

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
  `pip-audit`. Out of scope for this report.
- **BL-288 (load / performance)** is a separate feature; out of scope.

---

## 8. Open Backlog Items Filed

Per the Risk 5 mitigation in `THEME_DESIGN.md`, P0/P1 findings would be
filed as separate backlog items so this audit could ship fast.

**This audit identified zero P0 and zero P1 findings.** No new backlog
items are filed. The single P2 (config drift) is encoded in the probe's
baseline list and tracked there until the manual catches up.

---

## 9. Re-Audit Cadence

This is the first formal audit since v021. Recommended cadence:

- **Per release (lightweight):** the `test_audit.py` probes run as part
  of the standard CI pytest pass — every PR enforces the SQL-injection
  allowlist, seed-endpoint gate, path-traversal rejection, and config
  drift baseline.
- **Per Phase / quarterly (full):** repeat this manual review (route
  inventory, fresh AST patterns, threat model walk-through) before the
  next major capability phase or six months from now, whichever comes
  first.

---

**Audit complete.** No fixes required for v043 to ship; the single P2
config-drift finding is documentation hygiene tracked by the probe
baseline.
