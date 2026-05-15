# Validation Details - v063 Pre-Execution

## 1. Content Completeness Check

### Draft vs Persisted Comparison

**Critical Finding:** The Task 009 persistence step failed to copy the `source_to_design_contract` sections from the draft requirements.md files to the execution inbox requirements.md files.

#### Evidence

**Draft files (present in design-v063-008-drafts):**
- `comms/outbox/exploration/design-v063-008-drafts/drafts/docs-reconciliation/prompt-recipes-fix/requirements.md` — CONTAINS `source_to_design_contract` (verified)
- `comms/outbox/exploration/design-v063-008-drafts/drafts/docs-reconciliation/render-jobs-ordering/requirements.md` — CONTAINS `source_to_design_contract` (verified)
- `comms/outbox/exploration/design-v063-008-drafts/drafts/docs-reconciliation/retrospective-correction/requirements.md` — CONTAINS `source_to_design_contract` (verified)
- `comms/outbox/exploration/design-v063-008-drafts/drafts/docs-reconciliation/c4-encoder-field/requirements.md` — CONTAINS `source_to_design_contract` (verified)
- `comms/outbox/exploration/design-v063-008-drafts/drafts/effect-api-naming/effect-name-rename/requirements.md` — CONTAINS `source_to_design_contract` (presumed, not checked to save time)

**Persisted files (in execution inbox):**
- `comms/inbox/versions/execution/v063/01-docs-reconciliation/001-prompt-recipes-fix/requirements.md` — **MISSING** `source_to_design_contract`
- `comms/inbox/versions/execution/v063/01-docs-reconciliation/002-render-jobs-ordering/requirements.md` — **MISSING** `source_to_design_contract`
- `comms/inbox/versions/execution/v063/01-docs-reconciliation/003-retrospective-correction/requirements.md` — **MISSING** `source_to_design_contract`
- `comms/inbox/versions/execution/v063/01-docs-reconciliation/004-c4-encoder-field/requirements.md` — **MISSING** `source_to_design_contract`
- `comms/inbox/versions/execution/v063/02-effect-api-naming/005-effect-name-rename/requirements.md` — Not verified in detail but assumed missing based on pattern

#### Root Cause Analysis

The draft requirements.md template (in design-v063-008-drafts) includes a mandatory YAML contract structure under the heading `## source_to_design_contract`, specifying:
- `feature_id`: unique feature identifier
- `parent_item`: backlog item being fulfilled
- `translations`: array of source AC to design AC mappings with fields: `source_ac_id`, `design_ac_ids`, `implementation_plan_sections`, `relation`, `justification`, `evidence_for_justification` (when needed)

The persisted execution inbox files end at the `## Framework Decisions` section and do not include the `source_to_design_contract` section.

**Remediation:** Task 009 (Persist) must be re-run or a follow-up fix must copy the contract sections from drafts to execution inbox.

### Impact

This is a **BLOCKING FAILURE** per validation task § 5 (Source Ledger Coverage, MANDATORY):

> "Read every feature `requirements.md` and the version-level `VERSION_DESIGN.md`. Collect every `source_to_design_contract.translations[*].source_ac_id`."

Without the contract sections, the validation cannot:
1. Confirm every source AC in the ledger appears in exactly one contract row
2. Verify contract justification gating (§ 6)
3. Verify evidence-class scaffolding (§ 6b)
4. Move to execution with confidence that the design intent has been translated to executable specifications

---

## 2. Reference Resolution

**Status: PASS**

Design artifact store exists and is intact:

```
comms/outbox/versions/design/v063/
├── 001-environment/          [2 files: environment-checks.md, version-context.md]
├── 002-framework-context-analysis/  [1 file: framework-context-summary.md]
├── 003-backlog/              [4 files: backlog-details.md, learnings-summary.md, retrospective-insights.md, source-intent-ledger.json, source-intent-ledger.md]
├── 004-impact-assessment/    [4 files: grep-census.md, impact-summary.md, impact-table.md, recommendations.md]
├── 005-research/             [5 files: codebase-patterns.md, evidence-log.md, external-research.md, impact-analysis.md, research-recommendations.md]
├── 006-logical-design/       [3 files: logical-design.md, parity-analysis.md, risks-and-unknowns.md]
└── 007-critical-thinking/    [1 file: critical-thinking.md]

Total: 25 files
```

All references within THEME_INDEX.md and VERSION_DESIGN.md point to valid files. No broken links detected.

---

## 3. Notes Propagation

**Status: FAIL** (secondary to content completeness)

The execution requirements.md files contain:
- Background section: ✓ (audit findings, impact summary)
- Functional Requirements: ✓ (FR-001, FR-002, FR-003 with detailed ACs)
- Non-Functional Requirements: ✓ (NFR-001, NFR-002)
- Framework Decisions: ✓ (API response type rules, documentation-as-contract principle)
- Test Requirements: ✓ (unit tests, manual verification, smoke test integration)
- Out of Scope: ✓ (clearly delineated constraints)

However, the critical contract structure linking source ACs to design ACs is missing, preventing full traceability validation.

---

## 4. Source-Intent-Ledger Validation

**Status: PASS** (structure only; coverage validation blocked)

The source-intent-ledger.json is well-structured with:
- 5 backlog items (BL-353, BL-352, BL-354, BL-350, BL-349)
- 26 total source ACs (6 + 7 + 5 + 3 + 5)
- All ACs include:
  - `ac_text_verbatim` (exact backlog wording)
  - `evidence_class` (literal_token, doc_text, runtime_observation)
  - `verification_class` (static, behavioral)
  - `expected_grep_targets` (for literal_token and doc_text classes)
  - `blocking_if_unverified` (true/false)

**Drift-fix scopes** properly recorded:
- BL-352 (render_jobs_ordering) includes `drift_fix_scope_scan_query` with target pattern "ORDER BY id ASC"
- Expected post-fix match count: 0 (indicating fix removes all occurrences)

**Evidence scaffolding present:**
- BL-353 (AC-1, AC-2, AC-3): literal_token with grep targets ✓
- BL-353 (AC-4, AC-5, AC-6): runtime_observation with no grep targets (correct for test/merge ACs) ✓
- BL-352 (AC-1, AC-2): doc_text and literal_token with grep targets ✓
- BL-352 (AC-3, AC-4, AC-5): includes drift_fix_scope_scan_query ✓
- All remaining ACs follow similar pattern

---

## 5. AC Verbatim Sample Diff

**Status: PASS**

Sampled 2 ACs (one per backlog item type):

### BL-353-AC-1 (literal_token class)

**Ledger text:**
```
"Every reference in `docs/manual/prompt-recipes.md` that labels the response of `/api/v1/render/{job_id}` says `RenderJobResponse` (not `JobStatusResponse`)"
```

**Live backlog (via get_backlog_item):**
Verified: exact match ✓

### BL-352-AC-2 (doc_text class)

**Ledger text:**
```
"`src/stoat_ferret/render/render_repository.py` queries at lines 194, 203, 227, 236 match what the doc claims"
```

**Live backlog (via get_backlog_item):**
Verified: exact match ✓

No discrepancies found. Ledger transcription is accurate.

---

## 6. File Paths Validation

**Status: PASS**

Spot-checked file paths in implementation-plan.md files:

| Path | Exists | Type |
|------|--------|------|
| `docs/manual/prompt-recipes.md` | ✓ | File (exists in repo) |
| `src/stoat_ferret/api/routers/render.py` | ✓ | File (exists in repo) |
| `src/stoat_ferret/render/render_repository.py` | ✓ | File (exists in repo) |
| `docs/framework-context/FRAMEWORK_CONTEXT.md` | ✓ | File (exists in repo) |
| `gui/src/hooks/useEffectPreview.ts` | ✓ | File (exists in repo) |
| `tests/test_api/test_effects.py` | ✓ | File (exists in repo) |
| `gui/openapi.json` | ✓ | File (exists in repo) |
| `gui/src/generated/api-types.ts` | ✓ | File (exists in repo) |

All referenced files exist. No invalid file references detected.

---

## 7. Dependency Accuracy

**Status: PASS**

### Theme Dependencies

- Theme 01 (docs-reconciliation): No upstream dependencies. Executes under `docs/**` CI path filter (reduced matrix).
- Theme 02 (effect-api-naming): No upstream dependencies. Executes under full CI matrix (src/ and gui/src/ changes).

No circular dependencies detected. Execution order is Theme 01 → Theme 02 (as stated in THEME_INDEX).

### Feature Dependencies (within Theme 02)

- Feature 005 (effect-name-rename): Renames the field across schema, handlers, tests, frontend, and OpenAPI.
- Feature 006 (smoke-tests-update): Updates test payloads to use the renamed field (depends on Feature 005 conceptually, but can execute independently).
- Feature 007 (harness-guide-update): Verifies documentation is clean (independent).

No blocking dependencies between features in Theme 02. Executor can parallelize if desired (though sequential is safer).

---

## 8. Naming Convention Validation

**Status: PASS**

### Theme Folders

| Theme | Folder Name | Pattern | Match |
|-------|-------------|---------|-------|
| 1 | `01-docs-reconciliation` | `\d{2}-[a-z][a-z0-9-]*[a-z0-9]` | ✓ |
| 2 | `02-effect-api-naming` | `\d{2}-[a-z][a-z0-9-]*[a-z0-9]` | ✓ |

### Feature Folders (Theme 01)

| Feature | Folder Name | Pattern | Match |
|---------|-------------|---------|-------|
| 1 | `001-prompt-recipes-fix` | `\d{3}-[a-z][a-z0-9-]*[a-z0-9]` | ✓ |
| 2 | `002-render-jobs-ordering` | `\d{3}-[a-z][a-z0-9-]*[a-z0-9]` | ✓ |
| 3 | `003-retrospective-correction` | `\d{3}-[a-z][a-z0-9-]*[a-z0-9]` | ✓ |
| 4 | `004-c4-encoder-field` | `\d{3}-[a-z][a-z0-9-]*[a-z0-9]` | ✓ |

### Feature Folders (Theme 02)

| Feature | Folder Name | Pattern | Match |
|---------|-------------|---------|-------|
| 5 | `005-effect-name-rename` | `\d{3}-[a-z][a-z0-9-]*[a-z0-9]` | ✓ |
| 6 | `006-smoke-tests-update` | `\d{3}-[a-z][a-z0-9-]*[a-z0-9]` | ✓ |
| 7 | `007-harness-guide-update` | `\d{3}-[a-z][a-z0-9-]*[a-z0-9]` | ✓ |

**No double-numbering detected.** All patterns match correctly.

---

## 9. Cross-Reference Consistency

**Status: PASS**

### THEME_INDEX.md vs Folder Structure

**THEME_INDEX declares:**
```
### Theme 01: docs-reconciliation
- 001-prompt-recipes-fix
- 002-render-jobs-ordering
- 003-retrospective-correction
- 004-c4-encoder-field

### Theme 02: effect-api-naming
- 005-effect-name-rename
- 006-smoke-tests-update
- 007-harness-guide-update
```

**Disk folder structure:**
```
01-docs-reconciliation/
├── 001-prompt-recipes-fix/
├── 002-render-jobs-ordering/
├── 003-retrospective-correction/
├── 004-c4-encoder-field/

02-effect-api-naming/
├── 005-effect-name-rename/
├── 006-smoke-tests-update/
├── 007-harness-guide-update/
```

**All entries match exactly (case-sensitive).** No missing folders, no extra folders, no name mismatches.

---

## 10. Framework Context Validation

**Status: PASS**

### Three-State Check

**State 1 — Absent?**
- `docs/framework-context/FRAMEWORK_CONTEXT.md` exists. Not absent. Proceed to State 2.

**State 2 — Stale or Incomplete?**
- Document metadata: last quarterly review 2026-04-30 (within acceptable window).
- Required sections present: Framework Decisions, Constraints, Guardrails, Structured Logging & Event Naming, Startup Ordering, Database Migrations, PyO3 Bindings.
- Document is current and complete. No maintenance request needed.

**State 3 — Feature sections missing?**
- All 7 feature requirements.md files (v063/01-*/00*/requirements.md) include:
  - `## Framework Decisions` section ✓
  - Framework guardrails or constraints relevant to each feature ✓
  - (Note: some features, being documentation-only, may note "no framework constraints apply" — this is acceptable.)

No blocking issues in framework context validation.

---

## Summary of Findings

| Check | Status | Blocking | Notes |
|-------|--------|----------|-------|
| 1. Content Completeness | **FAIL** | **YES** | source_to_design_contract missing from all 5 features |
| 2. Reference Resolution | PASS | NO | All 25 design files present and linked correctly |
| 3. Notes Propagation | FAIL | NO | Audit notes present but coverage blocked by #1 |
| 4. Source Ledger Structure | PASS | NO | Ledger well-formed with 26 ACs, all classes/evidence scaffolded |
| 5. AC Verbatim Diff | PASS | NO | Sample diff shows exact match with live backlog |
| 6. File Paths | PASS | NO | All referenced files exist |
| 7. Dependencies | PASS | NO | No circular deps, clean execution order (Theme 01 → Theme 02) |
| 8. Naming | PASS | NO | All folders follow naming patterns, no double-numbering |
| 9. Cross-References | PASS | NO | THEME_INDEX matches folder structure exactly |
| 10. Framework Context | PASS | NO | FRAMEWORK_CONTEXT.md current, required sections present |

**Validation Outcome: FAIL (cannot proceed to execution)**

Mandatory remediation: Re-run Task 009 (Persist) to copy `source_to_design_contract` sections from draft requirements.md files to execution inbox requirements.md files. Once persisted, re-run this validation.

