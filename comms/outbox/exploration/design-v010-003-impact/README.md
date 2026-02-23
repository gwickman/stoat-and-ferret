# Exploration: design-v010-003-impact

Impact assessment for v010 version design. Analyzed all 5 backlog items (BL-072, BL-073, BL-074, BL-077, BL-078) for documentation, tooling, process, and caller-adoption impacts.

## Produced

- `comms/outbox/versions/design/v010/003-impact-assessment/README.md` — Summary with recommendations for logical design
- `comms/outbox/versions/design/v010/003-impact-assessment/impact-table.md` — 18 impacts in tabular format
- `comms/outbox/versions/design/v010/003-impact-assessment/impact-summary.md` — Impacts grouped by classification (6 substantial, 12 small, 0 cross-version)

## Key Findings

- 8 caller-adoption risks identified, primarily around BL-073 (progress) and BL-074 (cancellation)
- The jobs router never wires the `progress` field from queue to API response
- The scan handler has no cancellation checkpoint and no progress reporting call
- The handler signature `(job_type, payload)` lacks job context needed for `set_progress(job_id, value)`
- The frontend cancel button is disabled during scanning and calls `onClose` not a cancel API
- No project-specific IMPACT_ASSESSMENT.md exists (normal for this project)
