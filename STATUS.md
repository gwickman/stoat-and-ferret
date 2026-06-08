# Project Status — stoat-and-ferret

**Current version:** v076 (Release 2, Wave 1 — Verify & Deliver)
**Status:** Completed 2026-06-08

## v076 Summary

Release 2, Wave 1 establishes the QC/compliance pass making ~14 of 17 UC-MEDIA-MPS-001 outcomes machine-verifiable, introduces delivery profiles with QC-gated export, embeds chapter metadata, and wires the Release 2 test layer.

### Delivered

| Theme | Feature | Status | PR |
|-------|---------|--------|----|
| qc-infrastructure | qc-namespace-declaration | ✓ | #526 |
| qc-infrastructure | rust-qc-parsers | ✓ | #527 |
| qc-infrastructure | qc-service-and-api | ✓ | #528 |
| qc-infrastructure | qc-api-smoke-tests | ✓ | #529 |
| delivery-and-export | delivery-profiles | ✓ | #530 |
| delivery-and-export | chapter-metadata-embedding | ✓ | #531 |
| delivery-and-export | delivery-smoke-and-docs | ✓ | direct |
| qc-as-test-layer | oc-mapping-test-layer | ✓ | direct |
| qc-as-test-layer | golden-qc-regression | ✓ | direct |
| acceptance-and-validation | chatbot-scenarios | ✓ | direct |
| acceptance-and-validation | browser-uat-journeys | ✓ | direct |
| acceptance-and-validation | uc-mps-001-acceptance-harness | ✓ | direct |

### Test Results

- **Test count:** 2811 passed, 20 skipped (2735 baseline → +76)
- **Regressions:** 0
- **FFmpeg-gated (deferred_post_merge):** BL-426 (chapter embedding), BL-458 (golden QC regression), BL-459 (acceptance harness)

### Key Capabilities Added

- **QC API** (`POST /api/v1/qc/run`, `GET /api/v1/qc/reports/{id}`, `GET /api/v1/render/{job_id}/qc`)
- **Delivery profiles** (`/api/v1/delivery-profiles` CRUD) with QC-gated render export
- **Chapter metadata embedding** via ffmetadata — Marker regions → FFmpeg CHAPTER sections
- **OC mapping** (`tests/qc/oc_mapping.py`) — 11 machine-verifiable outcomes mapped to check IDs
- **UAT journeys 701–706** — Release 2 markers, mastering, QC-fail, and stub journeys
- **UC-MEDIA-MPS-001 acceptance harness** — ≥14/17 OC pass assertion (FFmpeg-gated)

### Deferred (FFmpeg-gated)

- BL-426 ACs 1-5: chapter embedding integration tests (require `STOAT_TEST_FFMPEG=1`)
- BL-458 ACs 1-4: golden QC regression drift detection (require FFmpeg + live render)
- BL-459 ACs 1-4: full acceptance harness (require FFmpeg + live server)

Human-only OCs: OC-3 (no discontinuities), OC-4 (dynamic range), OC-5 (tonal balance), OC-14 (no sync drift) — see `docs/uat/tier2-perceptual-checklist.md`
