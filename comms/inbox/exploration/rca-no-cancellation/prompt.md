Investigate how job cancellation was omitted from the job queue and scan implementation, and why this wasn't caught.

**The issue:** `AsyncioJobQueue` has no cancel method, no cancel API endpoint, and the scan loop has no cancellation checkpoint. The frontend cancel button has nothing to call.

**Your task:** Full audit to trace how this happened.

1. Read the original design docs under `docs/design/` for anything specifying job cancellation, abort, or stop mechanisms
2. Review backlog items related to job queue, cancellation, and scan (search relevant terms)
3. Find which version(s) and theme(s) implemented the job queue and scan modal
4. Read the version design documents and implementation plans from comms/ folders
5. Read the retrospectives for those versions
6. Examine the delivered code for the job queue and scan modal cancel button
7. Based only on evidence, identify what process deficiencies allowed this gap
8. Check latest processes, code, and pending backlog for stoat-and-ferret and auto-dev-mcp for gaps already improved since
9. Recommend specific changes

Analysis only — do not make any changes or create any items.

## Output Requirements

Create findings in comms/outbox/exploration/rca-no-cancellation/:

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
git add comms/outbox/exploration/rca-no-cancellation/
git commit -m "exploration: rca-no-cancellation complete"
