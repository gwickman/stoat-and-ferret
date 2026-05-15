# Discrepancies Found - v063 Pre-Execution Validation

## Blocking Issues

### Issue #1: Missing source_to_design_contract Sections

**Severity:** BLOCKING — Prevents execution

**Affected:** All 5 feature requirements.md files
- `comms/inbox/versions/execution/v063/01-docs-reconciliation/001-prompt-recipes-fix/requirements.md`
- `comms/inbox/versions/execution/v063/01-docs-reconciliation/002-render-jobs-ordering/requirements.md`
- `comms/inbox/versions/execution/v063/01-docs-reconciliation/003-retrospective-correction/requirements.md`
- `comms/inbox/versions/execution/v063/01-docs-reconciliation/004-c4-encoder-field/requirements.md`
- `comms/inbox/versions/execution/v063/02-effect-api-naming/005-effect-name-rename/requirements.md`

**Description:** The `source_to_design_contract` YAML section, which maps every source acceptance criterion from the backlog item to design-phase acceptance criteria, is present in the draft requirements.md files (design-v063-008-drafts) but **absent** from the persisted execution inbox files.

**Expected Structure:** Each feature requirements.md should include a section like:

```markdown
## source_to_design_contract

```yaml
source_to_design_contract:
  feature_id: 001-prompt-recipes-fix
  parent_item: BL-353
  translations:
    - source_ac_id: BL-353-AC-1
      design_ac_ids: [FR-001-AC-1, FR-001-AC-2]
      implementation_plan_sections: ["plan §2"]
      relation: preserved
      justification: null
    # ... (one row per source AC)
```
```

**Impact on Validation:**
- Cannot verify source ledger coverage (validation task § 5)
- Cannot verify contract justification gating (validation task § 6)
- Cannot verify evidence-class scaffolding mappings (validation task § 6b)
- Executor lacks traceability from source intent to design, creating ambiguity during feature implementation

**Root Cause:** Task 009 (Persist) failed to copy the contract sections from draft files to execution inbox, or the persistence process truncated the files at the Framework Decisions section.

**Remediation:**
1. Re-run Task 009 (Persist) with the complete draft files as input
2. Alternatively, manually copy the `## source_to_design_contract` section from each draft file to the corresponding execution inbox file
3. Verify all 5 files now contain the contract section before re-running validation

---

## Warnings (Non-Blocking)

None. All other validation checks passed or are pending completion of the blocking issue.

---

## Verification Checklist for Remediation

After fixing the missing contract sections, verify:

- [ ] `comms/inbox/versions/execution/v063/01-docs-reconciliation/001-prompt-recipes-fix/requirements.md` contains 6 rows in translations (BL-353-AC-1 through AC-6)
- [ ] `comms/inbox/versions/execution/v063/01-docs-reconciliation/002-render-jobs-ordering/requirements.md` contains 7 rows in translations (BL-352-AC-1 through AC-7)
- [ ] `comms/inbox/versions/execution/v063/01-docs-reconciliation/003-retrospective-correction/requirements.md` contains 5 rows in translations (BL-354-AC-1 through AC-5)
- [ ] `comms/inbox/versions/execution/v063/01-docs-reconciliation/004-c4-encoder-field/requirements.md` contains 3 rows in translations (BL-350-AC-1 through AC-3)
- [ ] `comms/inbox/versions/execution/v063/02-effect-api-naming/005-effect-name-rename/requirements.md` contains 5 rows in translations (BL-349-AC-1 through AC-5)
- [ ] All contract rows include: `source_ac_id`, `design_ac_ids`, `implementation_plan_sections`, `relation`, `justification` (optional for preserved/refined/broadened, mandatory for narrowed/replaced/source_stale)
- [ ] Re-run validation with: `tool_help('validate_version_design', project='stoat-and-ferret', version='v063')`
- [ ] Confirm: all 16 checklist items now pass

---

## Related Backlog Items

No existing backlog items found for this specific persistence failure. However, this issue may relate to:
- BL-946 (README discipline principles, version task design refinements)
- BL-950 (Design task prompt migration to named deliverable files)

Consider filing a follow-up backlog item if this is a systematic issue across version design persists.

