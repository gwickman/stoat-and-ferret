# Process Analysis: How Auto-Dev Design and Retrospective Steps Work

## IMPACT_ASSESSMENT.md (Does Not Exist Yet)

**Purpose:** Project-specific checks that run during the design phase (Task 003: Impact Assessment). When a new version is being designed, the impact assessment step reads `docs/auto-dev/IMPACT_ASSESSMENT.md` and executes each check category defined there.

**How it works:** Task 003 (`design_version_prompt/task_prompts/003-impact-assessment.md`) runs generic impact checks for all projects, then reads IMPACT_ASSESSMENT.md for project-specific checks. If the file doesn't exist, it documents "No project-specific impact checks configured" and continues.

**Relevance to RCAs:** This is the ideal location for project-specific checks that would have prevented several RCA findings:
- **Async safety check:** Flag any feature plan that calls `subprocess.run()` or `time.sleep()` from async context
- **Settings documentation check:** If a version adds Settings fields, verify .env.example is updated
- **UX input mechanism check:** For GUI features with user input, verify appropriate input mechanisms
- **Cross-version wiring check:** For features consuming prior-version backends, list behavioral assumptions

Currently, stoat-and-ferret has no IMPACT_ASSESSMENT.md, so none of these checks run.

## VERSION_CLOSURE.md (Does Not Exist Yet)

**Purpose:** Project-specific closure checklist that runs during the retrospective phase (Task 009: Project-Specific Closure). After a version is complete, the closure step reads `docs/auto-dev/VERSION_CLOSURE.md` and executes each section's checklist.

**How it works:** Task 009 (`retrospective_prompt/task_prompts/009-project-specific-closure.md`) always runs a closure evaluation based on the version's actual changes (Step 1). If VERSION_CLOSURE.md exists, it also executes the checklist (Steps 3-4). It can launch sub-explorations for document updates and CI verification.

**Relevance to RCAs:** This is the ideal location for post-version checks that would have caught residual gaps:
- **Wiring audit expansion:** After each version, verify all write endpoints have corresponding GUI surfaces
- **Backlog completeness:** Verify all retrospective tech debt items have corresponding BL items
- However, many RCA recommendations are better suited to IMPACT_ASSESSMENT.md (design phase) than VERSION_CLOSURE.md (retrospective phase), because the goal is to prevent gaps during design rather than detect them after implementation.

Currently, stoat-and-ferret has no VERSION_CLOSURE.md, so only the generic closure evaluation runs.

## Design Phase: Key Steps

### Task 002: Backlog Analysis
Reads PLAN.md for version scope, fetches all backlog items, reviews previous retrospective, searches learnings. **Gap identified:** This step doesn't cross-reference backlog items against design-doc milestones to check for incomplete coverage (rca-no-cancellation R3).

### Task 003: Impact Assessment
Runs generic checks (documentation review, caller impact analysis) and project-specific checks (IMPACT_ASSESSMENT.md). **Gap identified:** No project-specific checks exist for stoat-and-ferret. This is where async safety checks and settings documentation checks should live.

### Task 006: Critical Thinking
Investigates risks from the logical design. Reviews coherence. **Gap identified:** This step validates that all backlog items are covered but doesn't check whether descoped items from requirements have backlog tracking.

### Task 007: Document Drafts
Creates VERSION_DESIGN.md, THEME_INDEX.md, THEME_DESIGN.md, requirements.md, and implementation-plan.md for each feature. The requirements Out of Scope sections are written here. **Gap identified:** No instruction to create backlog items for descoped design-doc features (rca-no-cancellation R1).

## Retrospective Phase: Key Steps

### Task 003: Backlog Verification
Cross-references BL items from PLAN.md with feature requirements, completes open items, checks for orphans. **Gap identified:** This step verifies completions and finds orphans but does NOT ingest new debt from theme retrospective tech-debt sections (rca-no-cancellation R2).

### Task 008: Generic Closure
Updates plan.md, verifies CHANGELOG, reviews README, checks repository state. Standard for all projects.

### Task 009: Project-Specific Closure
Evaluates closure needs based on actual changes, executes VERSION_CLOSURE.md if it exists. **Gap identified:** Without VERSION_CLOSURE.md, only a basic evaluation runs. No wiring audit or documentation completeness check occurs.

## Existing Learnings and Product Requests Overlap

### Learnings with RCA overlap:
- **LRN-016** (Validate Acceptance Criteria Against Codebase During Design) — Partially overlaps with rca-no-cancellation. LRN-016 covers unachievable criteria; the RCAs identify **missing** criteria. Different failure mode.
- **LRN-044** (Settings Consumer Traceability) — Partially overlaps with rca-no-env-example. LRN-044 covers code wiring; .env.example is documentation. Adjacent concerns.
- **LRN-014** (Template-Driven Process Improvements Over Standalone Documentation) — Directly supports the approach of embedding fixes into IMPACT_ASSESSMENT.md and prompt templates rather than standalone docs.

### No existing learning covers:
- "Schema without wiring" anti-pattern (deserves a learning)
- "Descoped without backlog" anti-pattern (deserves a learning)
- "Research findings not tracked as backlog" (deserves a learning)

### Product requests:
- **PR-003** (session health / context compaction) — Unrelated to RCA findings.
- No existing product request covers the process improvements recommended by the RCAs.

## Where Recommendations Map

| RCA Recommendation | Best Target | Rationale |
|---|---|---|
| Custom blocking-in-async lint | stoat-and-ferret CI/config | Project-specific tooling |
| Event-loop responsiveness test | stoat-and-ferret backlog | Project-specific test |
| Backlog items from research | auto-dev-mcp process | General process gap |
| End-to-end wiring in completion reports | auto-dev-mcp process | General process gap |
| Prior-version dependency verification | IMPACT_ASSESSMENT.md | Project-specific check |
| Schema-without-wiring learning | stoat-and-ferret learning | Knowledge capture |
| Track descoped as backlog | auto-dev-mcp process | General process gap |
| Retrospective debt ingestion | auto-dev-mcp process | General process gap |
| Wiring audit: absent endpoints | auto-dev-mcp process | General process gap |
| Async safety in design review | IMPACT_ASSESSMENT.md | Project-specific check |
| .env.example alongside settings | IMPACT_ASSESSMENT.md | Project-specific check |
| Fix API spec examples | stoat-and-ferret code | Local fix |
| UX checklist for GUI themes | IMPACT_ASSESSMENT.md | Project-specific check |
| ASYNC ruff rules | Not worth doing | Limited coverage for asyncio |
| Modal wireframes in design docs | Not worth doing | Retroactive, low value |
| Browse-button UX recommendations | Not worth doing | Feature request, not process |
| .env.example retrospective question | Not worth doing | Over-engineering |
| Design-doc traceability | Not worth doing | Over-engineered for payoff |
| Split Out of Scope sections | Not worth doing | Cosmetic; R1 is sufficient |
