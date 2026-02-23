# Design v010 — Document Drafts (Task 007)

Drafted complete design documents for v010 (Async Pipeline & Job Controls): 2 themes, 5 features, with VERSION_DESIGN.md, THEME_INDEX.md, per-theme THEME_DESIGN.md, and per-feature requirements.md + implementation-plan.md. All documents reference the design artifact store and are organized under `drafts/` with a manifest.json as the single source of truth for numbering and metadata.

## Document Inventory

| Document | Path |
|----------|------|
| manifest.json | `drafts/manifest.json` |
| VERSION_DESIGN.md | `drafts/VERSION_DESIGN.md` |
| THEME_INDEX.md | `drafts/THEME_INDEX.md` |
| Theme 1 Design | `drafts/async-pipeline-fix/THEME_DESIGN.md` |
| T1/F1 Requirements | `drafts/async-pipeline-fix/fix-blocking-ffprobe/requirements.md` |
| T1/F1 Impl Plan | `drafts/async-pipeline-fix/fix-blocking-ffprobe/implementation-plan.md` |
| T1/F2 Requirements | `drafts/async-pipeline-fix/async-blocking-ci-gate/requirements.md` |
| T1/F2 Impl Plan | `drafts/async-pipeline-fix/async-blocking-ci-gate/implementation-plan.md` |
| T1/F3 Requirements | `drafts/async-pipeline-fix/event-loop-responsiveness-test/requirements.md` |
| T1/F3 Impl Plan | `drafts/async-pipeline-fix/event-loop-responsiveness-test/implementation-plan.md` |
| Theme 2 Design | `drafts/job-controls/THEME_DESIGN.md` |
| T2/F1 Requirements | `drafts/job-controls/progress-reporting/requirements.md` |
| T2/F1 Impl Plan | `drafts/job-controls/progress-reporting/implementation-plan.md` |
| T2/F2 Requirements | `drafts/job-controls/job-cancellation/requirements.md` |
| T2/F2 Impl Plan | `drafts/job-controls/job-cancellation/implementation-plan.md` |

**Total: 15 documents** (1 manifest + 1 version design + 1 theme index + 2 theme designs + 5 requirements + 5 implementation plans)

## Reference Pattern

All documents are lean and reference the design artifact store:
- `comms/outbox/versions/design/v010/001-environment/` for environment context
- `comms/outbox/versions/design/v010/004-research/` for research evidence
- `comms/outbox/versions/design/v010/006-critical-thinking/` for risk assessment and investigation results

Documents do NOT duplicate artifact store content — they provide brief summaries and explicit references.

## Completeness Check

| Backlog Item | Theme | Feature | requirements.md | implementation-plan.md |
|---|---|---|---|---|
| BL-072 (P0) | async-pipeline-fix | fix-blocking-ffprobe | Yes | Yes |
| BL-077 (P2) | async-pipeline-fix | async-blocking-ci-gate | Yes | Yes |
| BL-078 (P2) | async-pipeline-fix | event-loop-responsiveness-test | Yes | Yes |
| BL-073 (P1) | job-controls | progress-reporting | Yes | Yes |
| BL-074 (P1) | job-controls | job-cancellation | Yes | Yes |

All 5 backlog items are covered. No deferrals.

## Format Verification

- THEME_INDEX.md feature lines match format `- \d{3}-[\w-]+: .+` (machine-parseable)
- manifest.json is valid JSON with all required fields
- No theme or feature slug starts with a digit prefix
- No placeholder text in any draft
- Backlog IDs cross-referenced against Task 002 backlog analysis
- All "Files to Modify" paths verified via Glob against actual codebase structure
  - Corrected: `tests/test_api/test_scan.py` (referenced in research) does not exist — replaced with `tests/test_api/test_videos.py` where scan-related tests live
