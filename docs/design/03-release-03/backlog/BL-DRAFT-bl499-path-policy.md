# BL-DRAFT-bl499-path-policy

**Status:** drafted, not filed
**Supersedes / amends:** BL-499 (currently "open — partial; colon escape remains")
**Evidence:** `poc-work/poc-4-escape-policy/retest-native/`, codex `10`
**Why now:** the residual BL-499 work is not "make Windows colon paths render" — it is "codify the chosen escape policy and verify it across all file-bearing filters". Two forms work; we must pick one and prove it.

## Problem statement

Per the 5-variant native-subprocess matrix in codex `10`, FFmpeg 8.0.1 accepts these forms for `lut3d=file=...`:

- `file=C\\:/.../file.cube` (double-backslash colon escape)
- `file='C\:/.../file.cube'` (single-quoted, single-backslash colon escape)
- `file=relative/file.cube` (controlled cwd)

And rejects these:

- `file=C:/.../file.cube`
- `file=C\:/.../file.cube` (single-backslash, unquoted)

The earlier conclusion "BL-499 NOT de-risked" in `09` was wrong. The real residual work is per-filter verification + a chosen policy.

## Proposed acceptance criteria

1. Run the 5-variant × 4-filter matrix (lut3d / subtitles / ass / movie) and produce `escape-policy-matrix.csv` listing exit code + observed size + stderr key line for each cell.
2. Recommend ONE escape policy (preferred: single-quoted-escaped because it composes with other expression-arg policy choices) and document the per-filter dispatch rule if any filter rejects the chosen policy.
3. Update the snf Rust path-emit helper (in or alongside `escape_for_filter` at `rust/stoat_ferret_core/src/ffmpeg/video.rs:23`) to emit the chosen form.
4. Add Rust unit tests pinning the policy: `assert!(emit_path("C:\\Users\\foo\\bar.cube") == "'C\\:/Users/foo/bar.cube'")` (or whatever the chosen form is).
5. Add an integration test that renders a real lut3d filter against a Windows-absolute path via native subprocess (no MSYS shell).

## Out of scope

- The non-Windows path case (Linux/macOS) — already works without escape.
- Subtitle text content escape (different problem; covered by BL-519 when it lands).

## Unit test seeds

```rust
#[test]
fn windows_path_emit_single_quote_escape() {
    use std::path::PathBuf;
    let p = PathBuf::from(r"C:\Users\foo\bar.cube");
    assert_eq!(emit_filter_option_path(&p).unwrap(), r"'C\:/Users/foo/bar.cube'");
}
#[test]
fn unix_path_emit() {
    use std::path::PathBuf;
    let p = PathBuf::from("/home/user/bar.cube");
    assert_eq!(emit_filter_option_path(&p).unwrap(), "'/home/user/bar.cube'");
}
#[test]
fn apostrophe_in_path_rejected() {
    use std::path::PathBuf;
    let p = PathBuf::from(r"C:\Users\foo\Bob's lut.cube");
    assert!(emit_filter_option_path(&p).is_err());
}
```

## Risks / open questions

- ~~Whether `subtitles`, `ass`, `movie` parsers honor the same escape forms as `lut3d`. Track 2 of the autonomous-derisking plan answers this.~~ **RESOLVED 2026-06-15:** Track 2 ran the full 5-variant × 4-filter matrix. All four filters accept variants 3 (double-backslash), 4 (single-quoted+escaped), and 5 (relative-cwd). All four reject variants 1 (unescaped) and 2 (single-backslash-unquoted). Results in `poc-work/poc-bl499-path-escape/policy.md` + `escape-policy-matrix.csv`.
- ~~Whether the snf renderer ever sees relative paths~~ **decided:** absolute paths are the design assumption; variant 5 (relative-cwd) drops out of the recommended policy.

## Scope clarification (added 2026-06-15 per codex `14`)

**This helper is for paths embedded inside FFmpeg filter option values** — `lut3d=file=...`, `subtitles=filename=...`, `ass=filename=...`, `movie=filename=...`. It is NOT for subprocess argv paths like `-i <input_path>` or `-y <output_path>`, which are opaque to FFmpeg's filter-graph parser and need no escaping.

Helper renamed to **`emit_filter_option_path`** (was `emit_filter_path`) so the scope is in the name.

## Recommended policy (added 2026-06-15)

**Variant 4 — single-quoted + colon escape: `<option>='<forward-slash-path-with-colon-escaped>'`**

Rust helper:
```rust
fn emit_filter_option_path(p: &Path) -> Result<String, &'static str> {
    let fwd = p.to_string_lossy().replace('\\', "/");
    if fwd.contains('\'') {
        return Err("path contains apostrophe; cannot safely single-quote-wrap");
    }
    let escaped = fwd.replace(':', r"\:");
    Ok(format!("'{}'", escaped))
}
```

### Apostrophe-in-path AC (added per codex `14`)

Windows filenames can legally contain `'`. A path like `C:\Users\foo\Bob's lut.cube` would break the `'<path>'` wrapping. The helper must either:

- **Reject deterministically** with a clear error at the API boundary (preferred for v1 — most likely paths don't have apostrophes, simple safety story), OR
- **Shell-style escape**: replace each `'` with `'\''` inside the wrapper (more permissive but more lexer surface area to test).

V1 ships rejection; v2 can add shell-style escape if usage data shows real users with apostrophes in asset paths.

Chosen over variant 3 (double-backslash) because:
1. **Single-quote wrapping is already the policy for expression-shaped filter args** (hue, scale, the new BL-502 geq pattern). One rule across all user-supplied values.
2. Less double-escape risk through multi-layer Rust string transforms.
3. Easier to spot wrongness in render logs.

## Evidence pointers

- `poc-work/poc-bl499-path-escape/policy.md` — Track 2 results + recommendation
- `poc-work/poc-bl499-path-escape/escape-policy-matrix.csv` — raw matrix
- `poc-work/poc-bl499-path-escape/test_matrix.py`, `test_matrix_fix.py` — reproducible harnesses
- `poc-work/poc-4-escape-policy/retest-native/test_lut3d.py` — original lut3d test (codex `10`)
- `10-codex-response.md` Section 5 — codex's verified variant matrix
