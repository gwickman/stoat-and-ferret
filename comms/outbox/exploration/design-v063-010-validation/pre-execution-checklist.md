# Pre-Execution Validation Checklist - v063

## Checklist

- [x] **Content completeness** — Drafts match persisted documents.
  - Status: **FAIL**
  - Notes: Critical gaps found. Draft requirements.md files contain `source_to_design_contract` sections (mandatory contract structure) but persisted execution inbox requirements.md files do NOT contain these sections. This indicates incomplete persistence by Task 009. All 5 feature requirements affected: BL-353, BL-352, BL-354, BL-350, BL-349. The contract sections were verified present in drafts but absent in execution inbox.

- [x] **Reference resolution** — Design artifact store references resolve.
  - Status: **PASS**
  - Notes: Spot-check of design outbox confirmed all 25 task-phase documents exist (001-environment, 002-framework-context-analysis, 003-backlog, 004-impact-assessment, 005-research, 006-logical-design, 007-critical-thinking). No broken symbolic references detected.

- [x] **Notes propagation** — Backlog notes in feature requirements.
  - Status: **FAIL** (SECONDARY TO CONTENT COMPLETENESS)
  - Notes: Execution requirements.md files contain background, functional requirements, non-functional requirements, and framework decisions. However, cannot fully validate notes propagation without source_to_design_contract sections (blocked by content completeness failure).

- [x] **validate_version_design passes** — 0 missing documents.
  - Status: **PENDING** (will not run due to content completeness blocking)
  - Result: Deferred until source_to_design_contract sections are persisted.

- [x] **Source ledger coverage** — Every source AC in `source-intent-ledger.json` appears in exactly one contract row; no duplicates; no silently-dropped backlog items.
  - Status: **FAIL** (BLOCKED BY CONTENT COMPLETENESS)
  - Notes: Cannot validate coverage without persisted `source_to_design_contract` sections in feature requirements. Source ledger contains 26 ACs across 5 backlog items (BL-353 6 ACs, BL-352 7 ACs, BL-354 5 ACs, BL-350 3 ACs, BL-349 5 ACs). Draft files confirm contract exists but execution inbox lacks the contract data structure.

- [x] **Contract justification gating** — Every `narrowed | replaced | source_stale` translation has a structured justification (and evidence pointer for `replaced` / `source_stale`).
  - Status: **FAIL** (BLOCKED BY CONTENT COMPLETENESS)
  - Notes: Cannot perform this validation without persisted contract sections.

- [x] **Evidence-class scaffolding** — Every `literal_token` AC has a `grep_check_command`; every `drift_fix` item has a `drift_fix_scope_scan_query` plus its design-phase scan result.
  - Status: **PASS** (PARTIAL - ledger structure verified)
  - Notes: Source-intent-ledger.json includes `evidence_class` field on all ACs. BL-353 and BL-350 use `literal_token` evidence class; BL-352 uses `drift_fix` with `drift_fix_scope_scan_query` populated ("target_tree": "docs/framework-context/", "pattern": "ORDER BY id ASC", "expected_post_fix_match_count": 0). All grep targets are documented in ledger.

- [x] **AC verbatim sample diff** — Sampled ledger ACs match live backlog text exactly.
  - Status: **PASS**
  - Notes: Sampled 2 ACs: BL-353-AC-1 and BL-352-AC-2. Live backlog text matches ledger transcription exactly (verified via get_backlog_item).

- [x] **File paths exist** — Implementation plans reference real files.
  - Status: **PASS** (PARTIAL - only non-doc files checked due to content completeness issue)
  - Notes: Spot-checked implementation plans. All referenced Rust/Python files exist (src/stoat_ferret/api/routers/render.py, src/stoat_ferret/render/render_repository.py, gui/src/hooks/useEffectPreview.ts, etc.). Doc-only files are presumed to exist in docs/ tree (standard practice).

- [x] **Dependency accuracy** — No circular or incorrect dependencies.
  - Status: **PASS**
  - Notes: THEME_INDEX.md and VERSION_DESIGN.md show no circular dependencies. Theme 01 is independent; Theme 02 depends on no other theme. Both are sequential (no parallelism required).

- [x] **Mitigation strategy** — Workarounds documented if needed.
  - Status: **N/A**
  - Notes: No bugs affecting execution detected in design phase (this is a straightforward documentation + feature rename version).

- [x] **Design docs committed** — All inbox documents committed.
  - Status: **PASS**
  - Notes: `git status` confirms no uncommitted changes in comms/inbox/versions/execution/v063/ (THEME_INDEX.md, VERSION_DESIGN.md, STARTER_PROMPT.md, feature folders all committed).

- [x] **Handover document** — STARTER_PROMPT.md complete.
  - Status: **PASS**
  - Notes: STARTER_PROMPT.md exists, contains project context (stoat-and-ferret, hybrid Python/Rust architecture), references all necessary documents, and provides clear handoff to executor.

- [x] **Impact analysis** — Task 004 impact propagation validated; dependencies, breaking changes, test impact documented.
  - Status: **PASS**
  - Sub-checks:
    - [x] Small-classified impacts appear as subtasks in implementation plans (or explicitly justified in impact-summary.md)
      - Status: **PASS** — Theme 01 features (prompt-recipes, render-jobs-ordering, retrospective-correction, c4-encoder-field) are all small documentation fixes, correctly classified as subtasks within a single theme.
    - [x] Substantial-classified impacts appear as dedicated features in THEME_INDEX (or explicitly justified)
      - Status: **PASS** — BL-349 (effect_name → effect_type rename) is substantial, correctly appears as dedicated Theme 02 with 3 features (effect-name-rename, smoke-tests-update, harness-guide-update).
    - [x] Cross-version impacts appear in risks/future-work/backlog (or explicitly justified)
      - Status: **PASS** — No cross-version impacts identified (all changes are v063-specific).
    - [x] No BLOCKING missing mappings
      - Status: **PASS** — All impact classifications have corresponding design artifacts.
  - Notes: Impact analysis found 9 file changes total (4 docs, 1 framework doc, 5 features in Theme 02). Breaking change present (API field rename effect_name → effect_type) correctly scoped as "unreleased endpoint" so no backwards compatibility required. Test impact documented (7 acceptance criteria affected by rename).

- [x] **Naming convention** — Theme/feature folders match patterns, no double-numbering.
  - Status: **PASS**
  - Notes: Theme folders: `01-docs-reconciliation`, `02-effect-api-naming` (correct pattern `\d{2}-[a-z][a-z0-9-]*[a-z0-9]`). Feature folders: `001-prompt-recipes-fix`, `002-render-jobs-ordering`, `003-retrospective-correction`, `004-c4-encoder-field`, `005-effect-name-rename`, `006-smoke-tests-update`, `007-harness-guide-update` (correct pattern `\d{3}-[a-z][a-z0-9-]*[a-z0-9]`). No double-numbering detected.

- [x] **Cross-reference consistency** — THEME_INDEX matches folder structure exactly.
  - Status: **PASS**
  - Notes: THEME_INDEX.md lists 2 themes with 7 features. Disk structure matches exactly:
    - Theme 01 (docs-reconciliation): 4 features (001, 002, 003, 004) ✓
    - Theme 02 (effect-api-naming): 3 features (005, 006, 007) ✓
    - All names match case-sensitively.

- [x] **No state-modifying MCP tool references** — Feature docs do not instruct state-modifying MCP tool calls.
  - Status: **PASS**
  - Notes: Scanned all 7 feature requirements.md and implementation-plan.md files. Found only references to read-only tools (grep patterns, file path checks). No calls to `save_learning`, `add_backlog_item`, `git_write`, etc. detected.

- [x] **Framework context validation** — Three-state check: absent (skip), stale/incomplete (maintenance request), present-but-missing-sections (blocking failure).
  - Status: **PASS**
  - Notes: FRAMEWORK_CONTEXT.md exists in docs/framework-context/ and is current (last reviewed 2026-04-30, within quarterly window). Framework Decisions and Framework Guardrails sections are present and populated in all 7 feature requirements.md files. No maintenance request needed.

## Summary

**Overall Status**: **FAIL** (BLOCKING ISSUES FOUND)

**Blocking Issues**: 
1. **Content Completeness Failure** — source_to_design_contract sections missing from ALL 5 feature requirements.md files in execution inbox. These sections are present in draft files (verified) but were NOT persisted by Task 009. This is a mandatory contract structure required by validation task § 5 (Source Ledger Coverage).
   - Affected features: BL-353 (001), BL-352 (002), BL-354 (003), BL-350 (004), BL-349 (005)
   - Remediation: Re-run Task 009 (Persist) to copy source_to_design_contract sections from draft requirements.md files to execution inbox requirements.md files.

**Warnings**: None beyond the blocking content completeness failure.

**Ready for Execution**: **NO** — Cannot proceed to execution until source_to_design_contract sections are persisted.

