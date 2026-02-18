# Task 006: Learning Extraction

Read AGENTS.md first and follow all instructions there, including the mandatory PR workflow.

## Objective

Extract transferable learnings from all completion reports and theme retrospectives, then save them via the learnings system.

## Context

Post-version retrospective for `${PROJECT}` version `${VERSION}`. Learnings capture reusable patterns, failure modes, and decision frameworks — not implementation details.

## Tasks

### 1. Read All Completion Reports

Read every completion report for `${VERSION}`:
- `comms/outbox/versions/execution/${VERSION}/<theme>/<feature>/completion-report.md`

For each report, identify:
- Patterns that worked well
- Approaches that failed and what replaced them
- Decision rationale worth preserving
- Debugging techniques that resolved issues

### 2. Read All Theme Retrospectives

Read every theme retrospective:
- `comms/outbox/versions/execution/${VERSION}/<theme>/retrospective.md`

For each retrospective, identify:
- Cross-feature patterns
- Theme-level learnings
- Process observations

### 3. Read Version Retrospective

Read:
- `comms/outbox/versions/execution/${VERSION}/retrospective.md`

Identify version-level insights not covered by individual themes.

### 4. Deduplicate and Filter

From all identified learnings:
- Remove duplicates (same insight from multiple sources)
- Remove implementation-specific details (code snippets, file paths)
- Remove version-specific references that won't generalize
- Verify causal claims before saving: if a completion report says "X failed because Y," check whether the evidence supports that causation or if it's post-hoc rationalization. Do not propagate unverified root-cause narratives as learnings. (See LRN-135.)
- Keep: transferable patterns, failure modes, decision frameworks, debugging approaches

### 5. Save Learnings

For each unique learning, call:

```python
save_learning(
    project="${PROJECT}",
    title="<concise title>",
    content="<full learning content in markdown>",
    tags=["<relevant-tags>"],
    source="${VERSION}/<theme>/<feature> completion-report" or "${VERSION}/<theme> retrospective",
    summary="<one-sentence summary>"
)
```

Content structure for each learning:
```markdown
## Context
[When this applies]

## Learning
[The transferable insight]

## Evidence
[What happened that demonstrated this]

## Application
[How to apply this in future work]
```

### 6. Check Existing Learnings for Updates

Call `list_learnings(project="${PROJECT}")` and check if any existing learnings should be updated based on new evidence from this version.

If an existing learning is reinforced or refined by new evidence, note it but do NOT modify existing learnings.

## Output Requirements

Save outputs to `comms/outbox/versions/retrospective/${VERSION}/006-learnings/`:

### README.md (required)

First paragraph: Learnings summary (X new learnings saved, Y existing reinforced).

Then:
- **New Learnings**: Table of title, tags, source
- **Reinforced Learnings**: Existing learnings that got additional evidence
- **Filtered Out**: Count and categories of items filtered (too specific, duplicates, etc.)

### learnings-detail.md

For each learning saved:
- Learning title
- Tags assigned
- Source document
- Full content saved

## Allowed MCP Tools

- `read_document`
- `save_learning`
- `list_learnings`
- `extract_learnings`
- `list_product_requests`
- `get_product_request`
- `add_product_request`
- `update_product_request`
- `upvote_item`

## Guidelines

- Focus on transferable insights, not implementation details
- Each learning must make sense without reading the source document
- Tags should enable discovery: use category tags (pattern, failure-mode, process, debugging)
- Do NOT modify existing learnings — only note reinforcement
- Do NOT commit — the master prompt handles commits
