Investigate how the Scan Directory UI was delivered without a Browse button for folder selection.

**The issue:** The Scan Directory feature requires users to manually type directory paths. There is no file/folder browser dialog despite this being a standard UX pattern for directory selection.

**Your task:** Full audit to trace how this happened.

1. Read the original design docs under `docs/design/` for anything specifying the scan directory UX, file pickers, or library browser interface
2. Review backlog items related to scan directory, library browser, and file selection (search relevant terms)
3. Find which version(s) and theme(s) implemented the scan directory UI
4. Read the version design documents and implementation plans from comms/ folders
5. Read the retrospectives for those versions
6. Examine the delivered ScanModal component code
7. Based only on evidence, identify whether a browse capability was specified but not implemented, never specified, or intentionally deferred
8. Check latest processes, code, and pending backlog for stoat-and-ferret and auto-dev-mcp for gaps already improved since
9. Recommend specific changes

Analysis only — do not make any changes or create any items.

## Output Requirements

Create findings in comms/outbox/exploration/rca-no-browse-button/:

### README.md (required)
Summary of findings and recommendations.

### evidence-trail.md
Chronological trace through design → backlog → version → implementation → retrospective.

### recommendations.md
Specific process/tooling changes recommended, noting already-addressed gaps.

## Guidelines
- Keep each document under 200 lines
- Cite specific documents, line numbers, timestamps
- Distinguish evidence from speculation

## When Complete
git add comms/outbox/exploration/rca-no-browse-button/
git commit -m "exploration: rca-no-browse-button complete"
