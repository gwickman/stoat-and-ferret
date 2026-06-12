# Theme Retrospective: wave-t-testing-harness

## Theme Overview
- **Version**: v080
- **Theme**: wave-t-testing-harness (Theme 3)
- **Goal**: Advance the Wave T testing thread (v075–v081): rewrite j_reverse_split.py to exercise v080 reverse/split APIs, regenerate the golden QC fixture with real FFmpeg measurements, complete the acceptance harness with ≥14/17 OC outcome assertions, add smoke coverage for four new effect types and the split endpoint, and update the smoke-test-harness guide.
- **Features**: 5 completed (2 partial, 3 fully complete), 0 failed

## Goal Achievement

Theme goal **partially achieved**. Three of the five sub-goals were fully met:

- **j_reverse_split.py rewritten**: real API assertions for project creation, reverse effect application, split, and clip boundary verification (Feature 009) ✅
- **Golden QC fixture regenerated**: BL-476 confirmed resolved (−21.75 LUFS, −21.07 dBTP); drift detection active (Feature 010) ✅
- **Smoke coverage and guide updated**: 4 effect smoke tests + split endpoint smoke test (Feature 012) and guide sections added (Feature 013) ✅

Partially met:

- **UAT journeys**: j_reverse_split.py rewritten but J-QC-Fail blocked by BL-480 (absent GUI surfaces); headless discharge of Journey 705 requires live server
- **Acceptance harness**: BL-476/BL-477 gates confirmed; Tier-2 checklist delivered; full end-to-end harness run (AC-1, AC-2, AC-4) deferred due to QC report HTTP 404 in test fixture environment

## Feature Summary

| Feature | Status | PR | Key Outcome |
|---------|--------|-----|-------------|
| 009-uat-journeys | partial | #590 | j_reverse_split.py rewritten with real API assertions; Tier-2 UAT checklist created |
| 010-golden-regression | complete | #588 | Golden QC fixture regenerated (BL-476 confirmed); drift detection active |
| 011-acceptance-harness | partial | #589 | BL-476/477 gates confirmed; Tier-2 checklist created; 3 FFmpeg/service-gated ACs deferred |
| 012-smoke-tests | complete | #589 | Smoke coverage for reverse, variable_speed, framerate_convert, freeze_frame, split |
| 013-smoke-harness-guide | complete | #591 | Guide updated with v080 effect types, split endpoint, STOAT_REVERSE_MAX_DURATION_S discharge |

## Theme Outcome Roll-Up (from outcome-evidence ledger)

| Metric | Count |
|--------|-------|
| Source ACs mapped to this theme | 12 |
| Supported | 7 |
| Weakened | 0 |
| Contradicted | 0 |
| Unverifiable | 0 |
| Deferred post-merge | 1 |
| Missing ledger entries (gaps) | 4 |

**Notes:**
- BL-457 (4 ACs): 3 supported (AC-1, AC-2, AC-4), 1 deferred_post_merge (AC-3, BL-480 blocker)
- BL-458 (4 ACs): all 4 supported
- BL-459 (4 ACs): 0 entries in evidence ledger (all 4 gaps); Feature 011 report documents AC-3 as supported, AC-1/AC-2/AC-4 as deferred_post_merge
- Features 012 and 013 are impact-mandate; no source BL ACs

## Quality Summary
- **Ruff Check**: 5/5 passed
- **Mypy**: 5/5 passed (122 source files, no issues)
- **CI**: 5/5 passed (23 checks per PR)

## Theme Test Baseline Summary

| Metric | Total |
|--------|-------|
| Inherited failures | 0 |
| Still failing | 0 |
| Incidentally fixed | 0 |
| New failures | 0 |

> Note: completion reports for this theme predate the test_baseline frontmatter schema; counts treated as 0.

## Framework Guidance Status

| Metric | Total |
|--------|-------|
| Features with framework guidance | N/A (pre-v087 reports) |

## Cross-Feature Patterns

1. **Prerequisite gate discipline**: Features 010 and 011 both confirmed BL-476 and BL-477 resolved before advancing — consistent cross-feature pre-execution gate pattern that prevented premature golden fixture commits.

2. **Impact-mandate bundling**: Features 012 (smoke tests) and 013 (guide update) were executed and merged in the same CI window as Feature 011, with 012 sharing PR #589. This minimized CI overhead for test-coverage + documentation work.

3. **Tier-2 checklist convergence**: Both Feature 009 and Feature 011 produced Tier-2 perceptual checklists covering OC-3/4/5/14. The documents are complementary: `tier2-uat-checklist.md` (journey-focused) and `tier2-acceptance-checklist.md` (harness-focused).

## Deviations from Design

- **Feature 011 full harness run deferred**: Design expected the acceptance harness to verify ≥14/17 OC outcomes. Code is correctly implemented (threshold=14, Tier-2 checklist wired), but QC report HTTP 404 in the test fixture environment blocked end-to-end execution. Discharge: UAT environment with real FFmpeg + QC service.

- **Feature 009 J-QC-Fail deferred**: Risk assessment anticipated this. `qc-status-fail` and `remaster-btn` testids absent from GUI (BL-480). No code gap; testids must be added to frontend after BL-480 resolution.

## Risks Encountered

- **BL-480 GUI surfaces absent** (anticipated): Blocked BL-457-AC-3 exactly as predicted. Deferred with explicit BL-480 dependency documented.
- **BL-476 resolved** (positive): FFmpeg produced real loudness measurements, unblocking Feature 010's golden fixture regeneration. Risk mitigated successfully.
- **Test fixture QC service unavailability** (unanticipated): Feature 011's full harness returned HTTP 404 on QC report fetch — environment-specific, not a code defect. Discharge path: UAT environment with FFmpeg.

## Learnings

1. **Live-server discharge pattern**: UAT journeys and the acceptance harness require a running server with FFmpeg. Features depending on these must include an explicit UAT-environment discharge path in their AC design; CI-only verification cannot satisfy them.

2. **Pre-gate confirmation saves scope ambiguity**: Confirming BL-476/BL-477 at the start of Features 010 and 011 (not mid-run) clarified what was achievable and prevented avoidable partial-completion paths.

3. **Impact-mandate features reduce ledger overhead**: Smoke and documentation features with no source BL ACs close cleanly; planning them as same-batch work alongside the BL-item feature they cover reduces overall CI cost.
