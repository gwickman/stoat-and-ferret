# Project Status — stoat-and-ferret

**Current version:** v090 (Asset Library + Image Clips + Generic Procedural Parser + Builder Validation Hardening)
**Status:** Completed 2026-06-28

## v090 Summary

v090 delivers four capability areas across three themes: a user asset library REST API with full CRUD and security hardening (BL-515), image clips as a schema-complete persisted clip type with an explicit render-path deferral guard (BL-511), a bespoke Rust recursive-descent expression parser powering `GenericProceduralImageBuilder` with per-pixel evaluation and safety bounds (BL-514), and Rust builder validation hardening covering IEEE 754 finiteness guards in six builders, empty/whitespace expression guards in HueRotation and Zoompan, and a UAT runner dependency edge fix (BL-567/568/569/570/571/572).

### Delivered

| Theme | Feature | Status | PR |
|-------|---------|--------|----|
| user-asset-library | asset-library-backend | ✓ | #680 |
| user-asset-library | asset-api-smoke-tests | ✓ | #681 |
| image-content-pipeline | image-clip-schema | ✓ | #682 |
| image-content-pipeline | generic-procedural-image-builder | ✓ | #683 |
| rust-builder-validation-hardening | ieee754-nan-inf-guards | ✓ | #684 |
| rust-builder-validation-hardening | uat-dep-fix | ✓ | #685 |
| rust-builder-validation-hardening | empty-expression-guards | ✓ | #686 |

### Test Results

- **Test count:** 3403 passed (baseline 3322, +81)
- **Regressions:** 0
- **Scope-deferred:** BL-511-AC-3 (image clip render path), BL-511-AC-7 (image clip composition test)
- **FFmpeg-gated (deferred_post_merge):** BL-569-AC-8 (NaN/inf FFmpeg integration contract), BL-570-AC-7 (NaN/inf FFmpeg integration contract)

### Key Capabilities Added

- **User asset library REST API** — full CRUD for user-owned assets (`/users/{user_id}/assets`); security hardening with ownership checks, path traversal prevention, file type allowlist; multi-platform smoke test coverage (BL-515, PRs #680–#681)
- **Image clip schema + persistence** — `ImageClip` model, DB migration, router endpoints, and an explicit `NotImplementedError` render-path guard signalling the deferred BL-511-AC-3 milestone; clip type registered in the factory (BL-511, PR #682)
- **GenericProceduralImageBuilder** — Rust recursive-descent expression parser with per-pixel RGBA evaluation, depth limit (32), op budget (10k/pixel), pow clamp (±100), per-row timeout, and PyO3 bindings; stub updated (BL-514, PR #683)
- **IEEE 754 finiteness guards** — NaN/±inf rejected at construction in six Rust builders and shape generators; unit-tested (BL-569/BL-570/BL-572, PR #684)
- **Empty/whitespace expression guards + u32→i64 promotion** — HueRotation and Zoompan builders now reject blank expressions; Zoompan frame count promoted from u32 to i64 to match FFmpeg contract (BL-567/BL-568, PR #686)
- **UAT dependency fix** — J501 wired as a prerequisite of J204 in `JOURNEY_DEPS`; UAT runner no longer skips J501 due to missing edge (BL-571, PR #685)

### Deferred (scope / FFmpeg-gated)

- BL-511-AC-3: Image clip render path — out of v090 scope; marked with `NotImplementedError` guard pending full render integration
- BL-511-AC-7: Image clip composition test — out of v090 scope; deferred with BL-511-AC-3
- BL-515-AC-14: Asset library edge case — pending BL-511 render path completion
- BL-569-AC-8: IEEE 754 NaN/inf FFmpeg integration contract test (requires `STOAT_TEST_FFMPEG=1`)
- BL-570-AC-7: IEEE 754 NaN/inf FFmpeg integration contract test (requires `STOAT_TEST_FFMPEG=1`)
