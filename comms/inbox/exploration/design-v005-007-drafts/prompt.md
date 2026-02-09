Read AGENTS.md first and follow all instructions there.

## Objective

Draft the complete content for all design documents: VERSION_DESIGN.md, THEME_INDEX.md, THEME_DESIGN.md per theme, and requirements.md + implementation-plan.md per feature for stoat-and-ferret version v005. Documents must be lean and reference the design artifact store.

## Context

This is Phase 3 (Document Drafts & Persistence) for stoat-and-ferret version v005. The refined logical design from Phase 2 (Task 006) is complete.

**WARNING:** Do NOT modify any files in `comms/outbox/versions/design/v005/`. These are the reference artifacts. If you find errors, document them and STOP.

## Tasks

### 1. Read the Design Artifact Store

Read ALL outputs from the centralized store:
- `comms/outbox/versions/design/v005/001-environment/README.md`
- `comms/outbox/versions/design/v005/001-environment/version-context.md`
- `comms/outbox/versions/design/v005/002-backlog/README.md`
- `comms/outbox/versions/design/v005/002-backlog/backlog-details.md`
- `comms/outbox/versions/design/v005/004-research/README.md`
- `comms/outbox/versions/design/v005/004-research/codebase-patterns.md`
- `comms/outbox/versions/design/v005/004-research/external-research.md`
- `comms/outbox/versions/design/v005/004-research/evidence-log.md`
- `comms/outbox/versions/design/v005/005-logical-design/logical-design.md`
- `comms/outbox/versions/design/v005/005-logical-design/test-strategy.md`
- `comms/outbox/versions/design/v005/006-critical-thinking/refined-logical-design.md`
- `comms/outbox/versions/design/v005/006-critical-thinking/risk-assessment.md`

Use Task 006's `refined-logical-design.md` as the PRIMARY design source.

### 2. Draft VERSION_DESIGN.md

Create version-level design document. Keep it lean — reference the artifact store for details.

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

For EACH theme, create a lean THEME_DESIGN.md with goal, features table, dependencies, technical approach, and risks.

### 5. Draft requirements.md (per feature)

For EACH feature, create requirements.md with:
- Goal (one sentence)
- Background (context, backlog items)
- Functional Requirements (FR-001, FR-002, etc. with acceptance criteria)
- Non-Functional Requirements (NFR-001, etc. with metrics)
- Property Test Invariants (PT-001, etc. — when the feature has pure functions, round-trips, or domain invariants)
- Out of Scope (explicit boundaries)
- Test Requirements (from Task 005/006 test strategy)
- Reference: `See comms/outbox/versions/design/v005/004-research/ for supporting evidence`

**CRITICAL — Backlog ID Cross-Reference:**
When writing the "Backlog Item: BL-XXX" line, cross-reference against the backlog analysis (002-backlog/backlog-details.md). Do NOT write BL numbers from memory. Verify each BL number matches the correct feature.

### 6. Draft implementation-plan.md (per feature)

For EACH feature, create implementation-plan.md with:
- Overview (2-3 sentences)
- Files to Create/Modify (table with actions)
- Implementation Stages (Stage 1, Stage 2, etc. with verification commands)
- Test Infrastructure Updates
- Quality Gates (standard commands)
- Risks (reference 006-critical-thinking/risk-assessment.md)
- Commit Message (template)

### 7. Create manifest.json

Create `drafts/manifest.json` with this schema:
```json
{
  "version": "v005",
  "description": "Version description text here",
  "backlog_ids": ["BL-003", "BL-028", "BL-029", "BL-030", "BL-031", "BL-032", "BL-033", "BL-034", "BL-035", "BL-036"],
  "context": {
    "rationale": "...",
    "constraints": ["..."],
    "assumptions": ["..."],
    "deferred_items": []
  },
  "themes": [
    {
      "number": 1,
      "slug": "theme-slug-here",
      "goal": "Theme goal text here",
      "features": [
        {"number": 1, "slug": "feature-slug-here", "goal": "Feature goal text"}
      ]
    }
  ]
}
```

**CRITICAL — Slug Naming:**
- Theme slugs must NOT include number prefixes (use `config-and-guidance`, not `01-config-and-guidance`)
- Feature slugs must NOT include number prefixes (use `windows-bash-guidance`, not `001-windows-bash-guidance`)
- The MCP tools add number prefixes automatically — passing prefixed names causes double-numbering

## Output Requirements

Create in `comms/outbox/exploration/design-v005-007-drafts/`:

### README.md (required)

First paragraph: Summary of document drafts created (X themes, Y features).

Then:
- **Document Inventory**: List of all drafted documents
- **Reference Pattern**: How documents reference the artifact store
- **Completeness Check**: All backlog items covered
- **Format Verification**: Machine-parseable formats validated

### draft-checklist.md

Verification checklist:
- [ ] manifest.json is valid JSON with all required fields
- [ ] Every theme in manifest has a corresponding folder under drafts/
- [ ] Every feature in manifest has both requirements.md and implementation-plan.md
- [ ] VERSION_DESIGN.md and THEME_INDEX.md exist in drafts/
- [ ] THEME_INDEX feature lines match format `- \d{3}-[\w-]+: .+`
- [ ] No placeholder text in any draft
- [ ] All backlog IDs from manifest appear in at least one requirements.md
- [ ] No theme or feature slug starts with a digit prefix
- [ ] Backlog IDs in each requirements.md cross-referenced against Task 002 backlog analysis

### drafts/ folder (structured output)

Write each document as an individual file under `drafts/`:

1. `drafts/manifest.json`
2. `drafts/VERSION_DESIGN.md`
3. `drafts/THEME_INDEX.md`
4. For each theme: `drafts/{theme-slug}/THEME_DESIGN.md`
5. For each feature: `drafts/{theme-slug}/{feature-slug}/requirements.md` and `drafts/{theme-slug}/{feature-slug}/implementation-plan.md`

## Allowed MCP Tools

- `read_document`

(All content should come from the design artifact store)

## Guidelines

- ALL backlog items from PLAN.md are MANDATORY — every item must appear in a feature's requirements.md
- Documents must be LEAN — reference the artifact store, don't duplicate it
- Follow machine-parseable format for THEME_INDEX.md exactly
- Include all acceptance criteria from backlog items
- Test requirements should match Task 005/006 test strategy
- Implementation plans should reference specific files based on research
- Theme/feature slugs in the drafts/ folder must NOT include number prefixes
- Do NOT modify the design artifact store

Do NOT commit or push — the calling prompt handles commits. Results folder: design-v005-007-drafts.