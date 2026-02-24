# v011 Theme Index

## Execution Order

Execute themes in order. Each theme must complete before starting the next.

### Theme 01: scan-and-clip-ux

**Path:** `comms/inbox/versions/execution/v011/01-scan-and-clip-ux/`
**Goal:** Deliver the missing GUI interaction layer for media scanning and clip management. The browse button (BL-070) validates the full-stack GUI pipeline by adding a new backend endpoint and frontend component, while clip CRUD (BL-075) wires the frontend to existing backend endpoints — closing a gap deferred since v005.

**Features:**

- 001-browse-directory: Add backend directory listing endpoint and frontend browse button to ScanModal.
- 002-clip-crud-controls: Add Add/Edit/Delete clip controls to ProjectDetails with form modals and state management.
### Theme 02: developer-onboarding

**Path:** `comms/inbox/versions/execution/v011/02-developer-onboarding/`
**Goal:** Reduce onboarding friction and establish project-specific design-time quality checks. Creates the missing .env.example template, documents the Windows /dev/null pitfall, and defines impact assessment checks that catch recurring issue patterns at design time rather than in production.

**Features:**

- 001-env-example: Create .env.example with all Settings fields documented.
- 002-windows-dev-guidance: Add Windows Git Bash /dev/null guidance to AGENTS.md.
- 003-impact-assessment: Create IMPACT_ASSESSMENT.md with 4 project-specific design checks.
## Notes

- Each feature folder contains requirements.md and implementation-plan.md
- Output documents go to comms/outbox/
- Follow AGENTS.md for implementation process
