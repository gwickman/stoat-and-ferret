# 09 — Security Audit: Rust Sanitization & Input Validation

## Scope

This audit covers Rust sanitization functions exposed via PyO3 bindings and
the Python-layer path validation for the scan endpoint. The review targets
OWASP-relevant attack vectors: path traversal, null byte injection, shell
injection, and whitelist bypass.

**Out of scope:** Network security, authentication, third-party dependency
audit (cargo-audit, pip-audit), full penetration testing.

## Architecture Context

The application uses a defence-in-depth model:

- **Rust layer** (`stoat_ferret_core::sanitize`): Low-level input validation
  and FFmpeg filter text escaping. Enforces type safety, null byte rejection,
  and whitelist validation for codecs/presets.
- **Python layer** (`stoat_ferret.api`): Business-logic validation including
  directory allowlists (`ALLOWED_SCAN_ROOTS`) and HTTP-level error handling.
- **FFmpeg execution**: Commands are built using `std::process::Command`,
  which bypasses the shell entirely, eliminating shell injection as a vector.

## Audit Findings

### 1. `escape_filter_text` — FFmpeg Filter Text Escaping

| Attribute | Detail |
|-----------|--------|
| **File** | `rust/stoat_ferret_core/src/sanitize/mod.rs:181-197` |
| **Attack vector** | FFmpeg filter syntax injection |
| **Coverage** | Complete |
| **Finding** | No issues |

**Analysis:** Escapes all FFmpeg filter metacharacters: `\`, `'`, `:`, `[`,
`]`, `;`, `\n`, `\r`. Operates on `chars()` for UTF-8 safety. Shell
metacharacters (`$`, `` ` ``, `|`) are intentionally not escaped because
FFmpeg commands use `std::process::Command` (no shell parsing).

**Verdict:** Secure for its intended scope.

### 2. `validate_path` — Path Safety Check

| Attribute | Detail |
|-----------|--------|
| **File** | `rust/stoat_ferret_core/src/sanitize/mod.rs:230-238` |
| **Attack vector** | Null byte injection, path traversal |
| **Coverage** | Partial (by design) |
| **Finding** | Known limitation — path traversal deferred to Python |

**Analysis:** Rejects empty paths and paths containing null bytes. Does NOT
check for path traversal sequences (`../`, `..\\`). This is documented at
line 205-206 and is intentional: the Rust layer provides minimal safety
(null byte = C string truncation attack), while the Python layer enforces
business-logic constraints (directory allowlists).

**Verdict:** Secure within its defined scope. Python-layer remediation
(`ALLOWED_SCAN_ROOTS`) implemented in this feature.

### 3. `validate_crf` — CRF Bounds Check

| Attribute | Detail |
|-----------|--------|
| **File** | `rust/stoat_ferret_core/src/sanitize/mod.rs` |
| **Attack vector** | Resource exhaustion via extreme encoding parameters |
| **Coverage** | Complete |
| **Finding** | No issues |

**Analysis:** Validates 0–51 range. Uses `u8` type, making negative values
impossible at the type level.

**Note (v012):** PyO3 binding removed — this function is now Rust-internal only.
Validation still occurs within `FFmpegCommand.build()`. Re-add trigger: Python-level
standalone validation need.

**Verdict:** Secure (Rust-internal).

### 4. `validate_speed` — Speed Multiplier Bounds

| Attribute | Detail |
|-----------|--------|
| **File** | `rust/stoat_ferret_core/src/sanitize/mod.rs` |
| **Attack vector** | Resource exhaustion, DoS via extreme speed values |
| **Coverage** | Complete |
| **Finding** | No issues |

**Analysis:** Validates 0.25–4.0 range. Rejects zero, negative, and extreme
values. NaN and infinity are rejected by the range check.

**Note (v012):** PyO3 binding removed — this function is now Rust-internal only.
Validation still occurs within `SpeedControl.new()`. Re-add trigger: Python-level
standalone validation need.

**Verdict:** Secure (Rust-internal).

### 5. `validate_volume` — Volume Multiplier Bounds

| Attribute | Detail |
|-----------|--------|
| **File** | `rust/stoat_ferret_core/src/sanitize/mod.rs:345-356` |
| **Attack vector** | Resource exhaustion via extreme amplification |
| **Coverage** | Complete |
| **Finding** | No issues |

**Analysis:** Validates 0.0–10.0 range. Limits amplification to prevent
audio clipping abuse.

**Verdict:** Secure.

### 6. `validate_video_codec` — Video Codec Whitelist

| Attribute | Detail |
|-----------|--------|
| **File** | `rust/stoat_ferret_core/src/sanitize/mod.rs:415-425` |
| **Attack vector** | Command injection via codec parameter |
| **Coverage** | Complete |
| **Finding** | No issues |

**Analysis:** Strict whitelist: `libx264`, `libx265`, `libvpx`, `libvpx-vp9`,
`libaom-av1`, `copy`. Case-sensitive matching. Existing Rust tests verify
injection attempts (`libx264; rm -rf /`, `$(whoami)`) are rejected.

**Verdict:** Secure.

### 7. `validate_audio_codec` — Audio Codec Whitelist

| Attribute | Detail |
|-----------|--------|
| **File** | `rust/stoat_ferret_core/src/sanitize/mod.rs:455-465` |
| **Attack vector** | Command injection via codec parameter |
| **Coverage** | Complete |
| **Finding** | No issues |

**Analysis:** Strict whitelist: `aac`, `libopus`, `libmp3lame`, `copy`.
Case-sensitive matching.

**Verdict:** Secure.

### 8. `validate_preset` — Encoding Preset Whitelist

| Attribute | Detail |
|-----------|--------|
| **File** | `rust/stoat_ferret_core/src/sanitize/mod.rs:496-506` |
| **Attack vector** | Command injection via preset parameter |
| **Coverage** | Complete |
| **Finding** | No issues |

**Analysis:** Strict whitelist of 10 standard FFmpeg presets. Case-sensitive
matching.

**Verdict:** Secure.

### 9. `scan_directory` — Python Scan Service

| Attribute | Detail |
|-----------|--------|
| **File** | `src/stoat_ferret/api/services/scan.py` |
| **Attack vector** | Path traversal, directory escape |
| **Coverage** | Previously partial, now complete |
| **Finding** | Gap remediated |

**Analysis (before this feature):** Only checked `Path.is_dir()`. No
restriction on which directories could be scanned. An attacker with API
access could scan any directory on the filesystem.

**Remediation:** Added `ALLOWED_SCAN_ROOTS` setting and
`validate_scan_path()` function. The scan endpoint now resolves paths via
`Path.resolve()` and checks containment against allowed roots. When the
allowlist is empty (default), all directories are permitted for
backwards-compatibility.

**Verdict:** Secure after remediation.

## Summary

| Function | Vectors Tested | Coverage | Status |
|----------|---------------|----------|--------|
| `escape_filter_text` | FFmpeg syntax injection, UTF-8 | Complete | Pass |
| `validate_path` | Null byte, empty path | Partial (by design) | Pass |
| `validate_crf` | Bounds overflow | Complete | Pass (Rust-internal, v012) |
| `validate_speed` | Extreme values, zero, negative | Complete | Pass (Rust-internal, v012) |
| `validate_volume` | Extreme amplification, negative | Complete | Pass |
| `validate_video_codec` | Injection, case bypass | Complete | Pass |
| `validate_audio_codec` | Injection, case bypass | Complete | Pass |
| `validate_preset` | Injection, case bypass | Complete | Pass |
| `scan_directory` | Path traversal, directory escape | Complete (after fix) | Pass |

## Remaining Gaps

1. **No authentication layer** — Any client with network access can invoke
   the scan endpoint. This is a known architectural gap (auth is out of scope
   for the current version).
2. **`ALLOWED_SCAN_ROOTS` defaults to empty** — In production deployments,
   operators should configure this to restrict scanning to media directories.

## Test Coverage

Security tests added in `tests/test_security/`:

- `test_path_validation.py`: 12 tests covering path traversal, null byte
  injection, symlink resolution, and `ALLOWED_SCAN_ROOTS` enforcement via API.
- `test_input_sanitization.py`: 19 tests covering shell injection in filter
  text, null byte injection, FFmpeg filter syntax injection, and whitelist
  bypass for codecs/presets.
