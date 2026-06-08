# Tier 2 Perceptual Checklist — UC-MEDIA-MPS-001

This checklist documents the outcomes from UC-MEDIA-MPS-001 that require headed (manual) perceptual assessment. These outcomes cannot be verified by automated QC checks and are excluded from `OC_HUMAN_ONLY` machine verification.

## How to use this checklist

Run after automated QC checks pass. A human reviewer listens to / views the output and marks each item pass/fail.

## Human-Only Outcome Checklist

| Outcome | Description | Pass criteria | Reviewer notes |
|---------|-------------|---------------|----------------|
| OC-3 | No perceptible discontinuities at section boundaries | Listener hears clean transitions between sections; no clicks, pops, or abrupt cuts | |
| OC-4 | Dynamic range preserved — no over-compression or pumping artifacts | Listener hears natural dynamics; no pumping or breathing from excessive compression | |
| OC-5 | Tonal balance appropriate to genre — no harsh EQ or mud | Listener hears balanced frequency content appropriate to the musical genre | |
| OC-14 | No perceptible sync drift over full duration | Viewer observes audio and video remain aligned; no gradual drift over program length | |

## When to run

- Before release sign-off
- After re-mastering a rejected deliverable
- When `tier2_checklist` is referenced by the acceptance harness (`tests/acceptance/uc_media_mps_001_harness.py`)

## Related

- Machine-verifiable OC mapping: `tests/qc/oc_mapping.py`
- Acceptance harness: `tests/acceptance/uc_media_mps_001_harness.py`
- UAT journeys: `tests/uat/journeys/j_mastering.py`, `j_qc_fail.py`
