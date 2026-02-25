## Task: Gather Backlog Item Sizing Evidence from v008–v012

Search through the design, implementation, and retrospective outputs for stoat-and-ferret versions v008 through v012 to find any comments, observations, or data about backlog item sizing accuracy — specifically cases where items were mis-sized and what the "real" size turned out to be.

### Where to Look

For each version (v008, v009, v010, v011, v012), read these document categories using read_document:

1. **Design documents**: `comms/outbox/versions/design/v0XX/` — look for size estimates assigned during planning
2. **Implementation outputs**: `comms/outbox/versions/execution/v0XX/` — look at completion reports, theme summaries for any sizing commentary
3. **Retrospective outputs**: `comms/outbox/versions/retrospective/v0XX/` — look at proposals, backlog verification, learnings for calibration findings
4. **Version state files**: Check version-state.json files for feature metadata

For each finding, record:
- Which version and document it came from
- The backlog item ID and title
- What size was estimated
- What size it actually was (or should have been)
- The evidence/reasoning for the correction
- The task type (e.g., documentation-only, deletion, refactor, greenfield, wiring, bug fix)

### What NOT to Do

- Do not create backlog items or learnings
- Do not modify any files
- Only gather and organize facts

### Output Requirements

Save all results to `comms/outbox/exploration/sizing-evidence-stoat/`:

- **README.md** — Summary of findings count and key patterns
- **sizing-evidence.md** — Complete table of all sizing evidence found, organized by version, with columns: Version, BL-ID, Title, Estimated Size, Actual Size, Task Type, Evidence Source, Reasoning

### Commit Instructions

Commit all results with message: `docs: sizing evidence gathering from v008-v012`