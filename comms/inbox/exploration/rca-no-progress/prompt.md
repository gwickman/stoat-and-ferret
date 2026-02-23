Investigate how the job queue was delivered without progress reporting and why this gap wasn't caught.

**The issue:** `AsyncioJobQueue`, `JobResult`, and `JobStatusResponse` have no progress field. The scan handler never reports intermediate progress. The frontend progress bar is permanently stuck at 0%.

**Your task:** Full audit to trace how this happened.

1. Read the original design docs under `docs/design/` for anything specifying job queues, progress reporting, or scan UX
2. Review backlog items related to job queue, scan, and progress (search relevant terms)
3. Find which version(s) and theme(s) implemented the job queue and scan UI
4. Read the version design documents and implementation plans from comms/ folders
5. Read the retrospectives for those versions
6. Examine the delivered code for the job queue and scan modal
7. Based only on evidence, identify what process deficiencies allowed this gap
8. Check latest processes, code, and pending backlog for stoat-and-ferret and auto-dev-mcp for gaps already improved since
9. Recommend specific changes

Analysis only — do not make any changes or create any items.

## Output Requirements

Create findings in comms/outbox/exploration/rca-no-progress/:

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
git add comms/outbox/exploration/rca-no-progress/
git commit -m "exploration: rca-no-progress complete"
