# Theme Index: v011

## 01-scan-and-clip-ux

Deliver the missing GUI interaction layer for media scanning and clip management. The browse button (BL-070) validates the full-stack GUI pipeline (new backend endpoint + frontend component), while clip CRUD (BL-075) wires the frontend to existing backend endpoints — closing a gap deferred since v005.

**Backlog Items:** BL-070, BL-075

**Features:**

- 001-browse-directory: Add backend directory listing endpoint and frontend browse button to ScanModal
- 002-clip-crud-controls: Add Add/Edit/Delete clip controls to ProjectDetails with form modals and state management

## 02-developer-onboarding

Reduce onboarding friction and establish project-specific design-time quality checks. Creates the missing .env.example template, documents the Windows /dev/null pitfall, and defines impact assessment checks that catch recurring issue patterns at design time.

**Backlog Items:** BL-019, BL-071, BL-076

**Features:**

- 001-env-example: Create .env.example with all Settings fields documented
- 002-windows-dev-guidance: Add Windows Git Bash /dev/null guidance to AGENTS.md
- 003-impact-assessment: Create IMPACT_ASSESSMENT.md with 4 project-specific design checks
