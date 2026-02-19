# Task 007: Document Drafts

Read AGENTS.md first and follow all instructions there.

## Objective

Draft the complete content for all design documents: VERSION_DESIGN.md, THEME_INDEX.md, THEME_DESIGN.md per theme, and requirements.md + implementation-plan.md per feature. Documents must be lean and reference the design artifact store.

## Context

This is Phase 3 (Document Drafts & Persistence) for `${PROJECT}` version `${VERSION}`.

The refined logical design from Phase 2 (Task 006) is complete. Now create the actual document content that will be persisted to the inbox.

**WARNING:** Do NOT modify any files in `comms/outbox/versions/design/${VERSION}/`. These are the reference artifacts. If you find errors, document them and STOP.

## Tasks

### 1. Read the Design Artifact Store

Read all outputs from the centralized store:
- `comms/outbox/versions/design/${VERSION}/001-environment/` — environment context
- `comms/outbox/versions/design/${VERSION}/002-backlog/` — backlog details
- `comms/outbox/versions/design/${VERSION}/004-research/` — research findings
- `comms/outbox/versions/design/${VERSION}/005-logical-design/` — original logical design
- `comms/outbox/versions/design/${VERSION}/006-critical-thinking/` — refined design and risk assessment

Use Task 006's `refined-logical-design.md` as the primary design source.

### 2. Draft VERSION_DESIGN.md

Create version-level design document. Keep it lean — reference the artifact store for details:

```markdown
# Version Design: ${VERSION}

## Description
[Version description and goals]

## Design Artifacts
Full design analysis available at: `comms/outbox/versions/design/${VERSION}/`

## Constraints and Assumptions
[Brief list — see 001-environment/version-context.md for full context]

## Key Design Decisions
[Brief list — see 006-critical-thinking/risk-assessment.md for rationale]

## Theme Overview
[Brief table of themes — see THEME_INDEX.md for details]
```

### 3. Draft THEME_INDEX.md

**CRITICAL: Machine-Parseable Format**

Parser regex: `- (\d+)-([\w-]+):`

**REQUIRED format for feature lists:**
```
**Features:**

- 001-feature-name: Brief description text here
- 002-another-feature: Another description text
```

**FORBIDDEN formats:**
- Numbered lists: `1.` `2.` `3.`
- Bold feature identifiers: `**001-feature-name**`
- Metadata before colon: `001-feature (BL-123, P0, XL)`
- Multi-line feature entries
- Missing colon after feature name

### 4. Draft THEME_DESIGN.md (per theme)

For EACH theme, create a lean THEME_DESIGN.md:

```markdown
# Theme: [name]

## Goal
[Theme objective — one paragraph]

## Design Artifacts
See `comms/outbox/versions/design/${VERSION}/006-critical-thinking/` for full risk analysis.

## Features
| # | Feature | Backlog | Goal |
|---|---------|---------|------|
| NNN | [slug] | BL-XXX | [one sentence] |

## Dependencies
[What must exist before this theme]

## Technical Approach
[High-level approach — reference 004-research/ for evidence]

## Risks
| Risk | Mitigation |
|------|------------|
| [Risk] | [See 006-critical-thinking/risk-assessment.md] |
```

### 5. Draft requirements.md (per feature)

For EACH feature, create requirements.md:
- Goal (one sentence)
- Background (context, backlog items)
- Functional Requirements (FR-001, FR-002, etc. with acceptance criteria)
- Non-Functional Requirements (NFR-001, etc. with metrics)
- Handler Pattern (conditional: only when the feature introduces new MCP tool handlers)
  - Pattern: sync or async (from Task 005 Handler Concurrency Decisions analysis)
  - Rationale: brief justification referencing I/O profile, event loop blocking, and concurrent caller assessment
  - If no new handlers, include "Not applicable for ${VERSION} — no new handlers introduced" or omit the section entirely
- Out of Scope (explicit boundaries)
- Test Requirements (from Task 005/006 test strategy)
- Reference: `See comms/outbox/versions/design/${VERSION}/004-research/ for supporting evidence`

**CRITICAL — Backlog ID Cross-Reference:**
When writing the "Backlog Item: BL-XXX" line in each feature's requirements.md, you MUST cross-reference the BL number against the backlog analysis (Task 002) or the feature-to-backlog mapping in the logical design (Task 005). Do NOT write BL numbers from memory. Verify that the BL number matches the correct function name. For example, if the backlog analysis says BL-020 is first() and BL-018 is unique(), do not accidentally write BL-018 in the first() requirements.

### 6. Draft implementation-plan.md (per feature)

For EACH feature, create implementation-plan.md:
- Overview (2-3 sentences)
- Files to Create/Modify (table with actions)
- Test Files (list of test file paths to run for this feature, e.g., `tests/test_backlog.py tests/test_theme.py` — used by execution prompts for targeted pytest runs instead of the full suite)
- Implementation Stages (Stage 1, Stage 2, etc. with verification commands)
- Test Infrastructure Updates (from test strategy)
- Quality Gates (standard commands)
- Risks (reference 006-critical-thinking/risk-assessment.md)
- Commit Message (template)

Use evidence from Task 004 research for specific approaches and values.

### 6a. Verify All File Paths (MANDATORY)

After drafting all implementation plans, you MUST verify every path in every "Files to Modify" table:

1. Collect all unique source file paths from all implementation plan "Files to Modify" tables
2. Call `request_clarification` with a `structure` query to list all files under the relevant source directories (e.g., `src/auto_dev_mcp/**/*.py`)
3. Compare each "Files to Modify" path against the structure listing
4. Any path NOT found in the listing must be corrected using the actual path from the listing
5. "Files to Create" paths are exempt — for these, verify only that the parent directory exists in the listing

You MUST NOT finalize implementation plans until all "Files to Modify" paths have been verified. Skipping this step has caused recurring errors in prior versions (v058: 6/10 plans had incorrect paths).

**Constraint:** `request_clarification` may ONLY be used for file path verification in this task. Do not use it for codebase research — that is Task 004's responsibility.

## Output Requirements

Create in `comms/outbox/exploration/design-${VERSION}-007-drafts/`:

### README.md (required)

First paragraph: Summary of document drafts created (X themes, Y features).

Then:
- **Document Inventory**: List of all drafted documents
- **Reference Pattern**: How documents reference the artifact store
- **Completeness Check**: All backlog items covered
- **Format Verification**: Machine-parseable formats validated

### drafts/ folder (structured output)

Write each document as an individual file under `drafts/`:

1. Create `drafts/manifest.json` with version metadata, theme/feature numbering, and goals
2. Write `drafts/VERSION_DESIGN.md` with version-level design
3. Write `drafts/THEME_INDEX.md` with machine-parseable theme/feature index
4. For each theme: create `drafts/{theme-slug}/THEME_DESIGN.md`
5. For each feature: create `drafts/{theme-slug}/{feature-slug}/requirements.md`
   and `drafts/{theme-slug}/{feature-slug}/implementation-plan.md`

#### manifest.json schema

```json
{
  "version": "${VERSION}",
  "description": "Version description text here",
  "backlog_ids": ["BL-XXX", "BL-YYY"],
  "context": {
    "rationale": "...",
    "constraints": ["..."],
    "assumptions": ["..."],
    "deferred_items": []
  },
  "themes": [
    {
      "number": 1,
      "slug": "config-and-guidance",
      "goal": "Theme goal text here",
      "features": [
        {"number": 1, "slug": "windows-bash-guidance", "goal": "Feature goal text"}
      ]
    }
  ]
}
```

The manifest is the single source of truth for numbering and metadata that Task 008 needs.

**CRITICAL — Slug Naming:**
- Theme slugs must NOT include number prefixes (use `config-and-guidance`, not `01-config-and-guidance`)
- Feature slugs must NOT include number prefixes (use `windows-bash-guidance`, not `001-windows-bash-guidance`)
- The MCP tools add number prefixes automatically — passing prefixed names causes double-numbering

#### Folder layout example

```
comms/outbox/exploration/design-${VERSION}-007-drafts/
├── README.md
├── draft-checklist.md
└── drafts/
    ├── manifest.json
    ├── VERSION_DESIGN.md
    ├── THEME_INDEX.md
    ├── config-and-guidance/
    │   ├── THEME_DESIGN.md
    │   └── windows-bash-guidance/
    │       ├── requirements.md
    │       └── implementation-plan.md
    └── critical-bug-fixes/
        ├── THEME_DESIGN.md
        ├── expose-missing-crud-tools/
        │   ├── requirements.md
        │   └── implementation-plan.md
        └── fix-model-config-propagation/
            ├── requirements.md
            └── implementation-plan.md
```

### draft-checklist.md

Verification checklist:
- [ ] manifest.json is valid JSON with all required fields
- [ ] Every theme in manifest has a corresponding folder under drafts/
- [ ] Every feature in manifest has a corresponding folder with both requirements.md and implementation-plan.md
- [ ] VERSION_DESIGN.md and THEME_INDEX.md exist in drafts/
- [ ] THEME_INDEX.md feature lines match format `- \d{3}-[\w-]+: .+`
- [ ] No placeholder text in any draft (`_Theme goal_`, `_Feature description_`, `[FILL IN]`, `TODO`)
- [ ] All backlog IDs from manifest appear in at least one requirements.md
- [ ] No theme or feature slug starts with a digit prefix (`^\d+-`)
- [ ] Backlog IDs in each requirements.md cross-referenced against Task 002 backlog analysis (no mismatches)
- [ ] All "Files to Modify" paths verified via `request_clarification` structure query (no unverified paths)

## Allowed MCP Tools

- `read_document`
- `request_clarification` (path verification only — see Section 6a)
- `list_product_requests`
- `get_product_request`
- `add_product_request`
- `update_product_request`
- `upvote_item`

(All content should come from the design artifact store. request_clarification is permitted solely for verifying file paths in implementation plans.)

## Guidelines

- ALL backlog items from PLAN.md are MANDATORY — every item must appear in a feature's requirements.md
- Documents must be LEAN — reference the artifact store, don't duplicate it
- Follow machine-parseable format for THEME_INDEX.md (see Section 3)
- Include all acceptance criteria from backlog items
- Test requirements should match Task 005/006 test strategy
- Implementation plans should reference specific files based on research
- Theme/feature slugs in the drafts/ folder must NOT include number prefixes — the MCP tools add them
- The consolidated document-drafts.md is no longer produced — use individual files with manifest.json
- Do NOT modify the design artifact store

## When Complete

```bash
git add comms/outbox/exploration/design-${VERSION}-007-drafts/
git commit -m "exploration: design-${VERSION}-007-drafts - document drafts complete"
git push
```
