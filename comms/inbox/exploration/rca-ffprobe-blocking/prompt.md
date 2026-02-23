Investigate how blocking `subprocess.run()` in `ffprobe_video()` was introduced and why it wasn't caught.

**The bug:** `src/stoat_ferret/ffmpeg/probe.py` uses synchronous `subprocess.run()` inside an async scan handler, freezing the entire asyncio event loop during scans.

**Your task:** Conduct a full audit to trace how this happened and what process gaps allowed it.

1. Read the original design docs under `docs/design/` for anything specifying ffprobe, scanning, or async patterns
2. Review the backlog items that led to ffprobe/scan implementation (search for ffprobe, scan, probe, video library)
3. Find which version(s) and theme(s) implemented this (list_versions, get_version_status, get_theme_status)
4. Read the version design documents and implementation plans from the comms/ folders
5. Read the retrospectives for those versions
6. Examine the actual code that was delivered
7. Based only on evidence found, identify what process deficiencies allowed this to slip through
8. Check the latest processes, code, and pending backlog for both stoat-and-ferret and auto-dev-mcp for any gaps already improved since
9. Recommend specific process or tooling changes

Do not make any changes, create backlog items, or modify any files other than your output documents.

## Output Requirements

Create findings in comms/outbox/exploration/rca-ffprobe-blocking/:

### README.md (required)
Summary of findings and recommendations.

### evidence-trail.md
Chronological trace through design → backlog → version → implementation → retrospective showing where the gap occurred.

### recommendations.md
Specific process/tooling changes recommended, noting which gaps have already been addressed.

## Guidelines
- Keep each document under 200 lines
- Cite specific documents, line numbers, and timestamps
- Distinguish evidence from speculation

## When Complete
git add comms/outbox/exploration/rca-ffprobe-blocking/
git commit -m "exploration: rca-ffprobe-blocking complete"
