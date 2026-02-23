Investigate how clip management controls were omitted from the GUI despite the backend having full CRUD support.

**The issue:** The ProjectDetails page displays clips read-only. Backend has complete clip CRUD (POST, PATCH, DELETE) — implemented and tested — but the GUI has no Add, Edit, or Delete buttons. Users cannot manage clips without direct API calls.

**Your task:** Full audit to trace how this happened.

1. Read the original design docs under `docs/design/` for anything specifying clip management, project GUI, or CRUD workflows
2. Review backlog items related to clips, project details GUI, and CRUD (search relevant terms)
3. Find which version(s) and theme(s) implemented clip endpoints and the project details GUI
4. Read the version design documents and implementation plans from comms/ folders
5. Read the retrospectives for those versions
6. Examine the delivered code for both backend clip endpoints and frontend project details
7. Based only on evidence, identify whether this was an intentional deferral, an oversight, or a scope cut — and what process gaps exist around tracking deferred work
8. Check latest processes, code, and pending backlog for stoat-and-ferret and auto-dev-mcp for gaps already improved since
9. Recommend specific changes

Analysis only — do not make any changes or create any items.

## Output Requirements

Create findings in comms/outbox/exploration/rca-clip-management/:

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
git add comms/outbox/exploration/rca-clip-management/
git commit -m "exploration: rca-clip-management complete"
