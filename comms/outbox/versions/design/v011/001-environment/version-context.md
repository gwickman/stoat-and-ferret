# Version Context — v011

## Version Goals

**v011 — GUI Usability & Developer Experience**

Close the biggest GUI interaction gaps and improve onboarding/process documentation.

**Dependency:** v010 deployed (completed 2026-02-23). Progress reporting from v010 is a prerequisite for scan UX improvements.

## Themes and Features

### Theme 1: scan-and-clip-ux
- 001-browse-button: Add file/directory browser dialog for scan path selection [BL-070, P2]
- 002-clip-management-controls: Add Add/Edit/Delete clip controls to project detail view [BL-075, P1]

### Theme 2: developer-onboarding
- 001-env-example: Create .env.example with all Settings fields documented [BL-071, P2]
- 002-windows-dev-guidance: Add /dev/null to nul guidance to AGENTS.md, add nul to .gitignore [BL-019, P3]
- 003-impact-assessment: Create IMPACT_ASSESSMENT.md with async safety, settings docs, cross-version wiring, and GUI input mechanism checks [BL-076, P1]

## Referenced Backlog Items

| ID | Priority | Brief |
|----|----------|-------|
| BL-019 | P3 | Windows dev guidance (/dev/null to nul) |
| BL-070 | P2 | Browse button for scan path selection |
| BL-071 | P2 | .env.example with Settings fields |
| BL-075 | P1 | Clip CRUD controls in project detail view |
| BL-076 | P1 | IMPACT_ASSESSMENT.md (async safety, settings, wiring, GUI inputs) |

*Full backlog item details will be gathered in Task 002.*

## Constraints and Dependencies

- **No inter-theme dependencies.** Themes 1 and 2 can be developed in parallel.
- **Intra-theme dependency (Theme 2):** .env.example (BL-071) should precede IMPACT_ASSESSMENT.md (BL-076) since the assessment checks for .env.example updates.
- **Risk:** BL-075 (clip CRUD GUI) touches multiple layers (GUI components, API routes, database). The browse button (BL-070) validates the GUI build pipeline first, so it's ordered before clip CRUD.

## Deferred Items to Be Aware Of

| Item | From | Status |
|------|------|--------|
| Drop-frame timecode support | M1.2 | TBD (deferred indefinitely) |
| Phase 3: Composition Engine | v008 (original) | post-v010 (still deferred) |
| BL-069: C4 documentation update | — | Excluded from version planning |

**Note:** C4 docs are 2 versions behind (last updated v008). BL-069 tracks this but is excluded from v011/v012 scope.

## Previously Completed Context

v010 (immediate predecessor) delivered:
- Async ffprobe with `asyncio.create_subprocess_exec()` replacing blocking `subprocess.run()`
- Ruff ASYNC rules as CI gate
- Event-loop responsiveness integration test
- Job progress reporting with per-file WebSocket updates
- Cooperative job cancellation with partial result saving

These v010 features (especially progress reporting) are prerequisites for v011's scan UX improvements.
