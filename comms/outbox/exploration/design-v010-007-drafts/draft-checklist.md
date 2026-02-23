# Draft Checklist — v010

- [x] manifest.json is valid JSON with all required fields
- [x] Every theme in manifest has a corresponding folder under drafts/
- [x] Every feature in manifest has a corresponding folder with both requirements.md and implementation-plan.md
- [x] VERSION_DESIGN.md and THEME_INDEX.md exist in drafts/
- [x] THEME_INDEX.md feature lines match format `- \d{3}-[\w-]+: .+`
- [x] No placeholder text in any draft (`_Theme goal_`, `_Feature description_`, `[FILL IN]`, `TODO`)
- [x] All backlog IDs from manifest appear in at least one requirements.md
- [x] No theme or feature slug starts with a digit prefix (`^\d+-`)
- [x] Backlog IDs in each requirements.md cross-referenced against Task 002 backlog analysis (no mismatches)
- [x] All "Files to Modify" paths verified via Glob structure query (no unverified paths)
- [x] No feature requirements.md or implementation-plan.md instructs MCP tool calls (features execute with Read/Write/Edit/Bash only)

## Verification Notes

**Backlog ID cross-reference:**
- BL-072 → fix-blocking-ffprobe requirements.md (confirmed: ffprobe blocking subprocess)
- BL-073 → progress-reporting requirements.md (confirmed: progress reporting)
- BL-074 → job-cancellation requirements.md (confirmed: job cancellation)
- BL-077 → async-blocking-ci-gate requirements.md (confirmed: CI quality gate for blocking calls)
- BL-078 → event-loop-responsiveness-test requirements.md (confirmed: integration test)

**File path corrections:**
- `tests/test_api/test_scan.py` referenced in research artifacts but does NOT exist in codebase
- Corrected to `tests/test_api/test_videos.py` (confirmed via Grep: scan_directory and ffprobe_video references found in test_videos.py, test_jobs.py, test_websocket_broadcasts.py, test_ffprobe.py)

**request_clarification note:**
- MCP `request_clarification` tool was unavailable during this task (connection error)
- File path verification completed using Glob and Grep tools directly against the codebase
- All unique source file paths from "Files to Modify" tables verified
