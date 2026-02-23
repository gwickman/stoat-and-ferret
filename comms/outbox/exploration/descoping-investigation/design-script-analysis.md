# Design Script Analysis: Anti-Descoping Rules

## Current Anti-Descoping Language

The design version prompts contain explicit anti-descoping rules in **7 of 9 task prompts**. All were introduced in commit `e241a73` (2026-02-08) and have been maintained through all subsequent template syncs (`ba173e2`, `8a39b24`, `db01281`).

### Task 002 — Backlog Analysis

File: `docs/auto-dev/PROMPTS/design_version_prompt/task_prompts/002-backlog-analysis.md`

> **MANDATORY SCOPE:** ALL backlog items listed in PLAN.md for this version are mandatory. No items may be deferred, descoped, or deprioritized. PLAN.md defines the version scope — it is not a suggestion. Read ALL backlog items and include ALL of them.

Guidelines section:
> ALL backlog items from PLAN.md are MANDATORY — no deferrals, no descoping

### Task 004 — Research Investigation

File: `docs/auto-dev/PROMPTS/design_version_prompt/task_prompts/004-research-investigation.md`

> ALL backlog items from PLAN.md are MANDATORY — research must cover all of them, no deferrals

### Task 005 — Logical Design

File: `docs/auto-dev/PROMPTS/design_version_prompt/task_prompts/005-logical-design.md`

> ALL backlog items from PLAN.md are MANDATORY and must be mapped to a feature — no deferrals, no descoping

### Task 006 — Critical Thinking

File: `docs/auto-dev/PROMPTS/design_version_prompt/task_prompts/006-critical-thinking.md`

In Validate Design Coherence (Section 6):
> ALL backlog items from PLAN.md still covered (mandatory scope — no deferrals allowed)

In Guidelines:
> ALL backlog items from PLAN.md are MANDATORY — risk investigation must not result in deferrals or descoping

### Task 007 — Document Drafts

File: `docs/auto-dev/PROMPTS/design_version_prompt/task_prompts/007-document-drafts.md`

> ALL backlog items from PLAN.md are MANDATORY — every item must appear in a feature's requirements.md

### Task 008 — Persist Documents

File: `docs/auto-dev/PROMPTS/design_version_prompt/task_prompts/008-persist-documents.md`

> ALL backlog items from PLAN.md are MANDATORY — verify all items appear in persisted documents before completing

### Task 009 — Pre-Execution Validation

File: `docs/auto-dev/PROMPTS/design_version_prompt/task_prompts/009-pre-execution-validation.md`

> ALL backlog items from PLAN.md are MANDATORY — any missing item is a blocking failure

Section 5 (Backlog Alignment):
> ALL backlog items from PLAN.md for this version are mandatory. No items may have been deferred or descoped.
> If any backlog item is missing, this is a BLOCKING FAILURE

## What the Rules Protect

The rules consistently protect one thing: **backlog items listed in PLAN.md cannot be removed from a version's scope.** Every task from analysis through validation enforces this.

## What the Rules Do NOT Protect

The rules do not:
1. Ensure design-doc specifications (roadmap milestones, API specs, GUI wireframes) are fully captured in backlog acceptance criteria
2. Prevent Out of Scope sections from listing items derived from design-doc features
3. Require backlog items to be created when an Out of Scope item defers a design-doc feature
4. Verify that backlog acceptance criteria are sufficient to fully deliver the design-doc intent

## No Design Theme Prompt

The `docs/auto-dev/PROMPTS/design_theme_prompt/` directory does not exist. Theme-level design is handled within the version design process (Task 007 drafts THEME_DESIGN.md per theme).

## AGENTS.md and CLAUDE.md

Neither file contains rules about descoping. AGENTS.md covers project structure, commands, coding standards, and PR workflow. CLAUDE.md references AGENTS.md.
