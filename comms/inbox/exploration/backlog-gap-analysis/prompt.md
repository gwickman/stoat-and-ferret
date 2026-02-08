Analyze the stoat-and-ferret project to identify backlog gaps for versions v004-v007 and suggest concrete backlog items.

## Context

Versions v001-v003 are complete. The project has a detailed roadmap at docs/design/01-roadmap.md mapping versions to milestones:
- v004: Milestones 1.8-1.9 (Testing infrastructure + quality verification)
- v005: Milestones 1.10-1.12 (GUI shell + library browser + project manager)
- v006: Milestones 2.1-2.3 (Effects engine foundation)
- v007: Milestones 2.4-2.6 (Effect Workshop GUI)

There are currently only 9 open backlog items (BL-003 through BL-019), most of which are technical debt from v001-v003 retrospectives. Very few, if any, map to the planned v004-v007 scope.

## Your Task

### Phase 1: Research (use sub-explorations for parallel work)

Use `start_exploration` to launch sub-investigations for parallel research. You can run multiple in parallel. Use `get_exploration_status` to poll for completion, and `get_exploration_result` to retrieve findings. Tell each sub-exploration to use `start_exploration` if it also wants to delegate sub-tasks.

Launch sub-explorations for:

1. **Codebase audit**: What exists today? Review the source code structure (src/, rust/, tests/) to understand what v001-v003 actually built. Look at the actual Python and Rust source files.

2. **Design doc review**: Read ALL design docs (docs/design/01-roadmap.md through 08-gui-architecture.md) to understand the full specifications for each milestone. Read them directly from the filesystem.

3. **Existing backlog analysis**: Read docs/auto-dev/BACKLOG.json to get current backlog items. Map existing items to planned versions.

4. **Version summaries**: Read version design docs or summaries from v001-v003 (look in docs/auto-dev/versions/) to understand what was delivered and what was deferred.

### Phase 2: Gap Analysis

For each version (v004-v007), compare:
- What the roadmap milestones specify
- What design docs detail (especially 07-quality-architecture.md for v004, 08-gui-architecture.md for v005)
- What existing backlog items already cover
- What's missing

### Phase 3: Backlog Suggestions

For each gap, produce a concrete backlog item suggestion with:
- **Title**: Clear, actionable
- **Priority**: P1 (critical for version), P2 (important), P3 (nice to have)
- **Tags**: Include target version tag (e.g., `v004`, `v005`)
- **Description**: What needs to be done and why
- **Acceptance criteria**: 3-5 measurable criteria
- **Size**: s/m/l estimate

Group suggestions by target version.

## Output Requirements

Create findings in comms/outbox/exploration/backlog-gap-analysis/:

### README.md (required)
First paragraph: Concise summary of gap analysis findings - how many gaps per version, key themes.
Then: Overview with links to detailed documents.

### v004-testing-infrastructure.md
Gap analysis and backlog suggestions for v004 (M1.8-1.9).

### v005-gui-shell.md
Gap analysis and backlog suggestions for v005 (M1.10-1.12).

### v006-effects-engine.md
Gap analysis and backlog suggestions for v006 (M2.1-2.3).

### v007-effect-workshop.md
Gap analysis and backlog suggestions for v007 (M2.4-2.6).

### existing-backlog-mapping.md
Analysis of how existing open backlog items map to planned versions, plus any orphaned items.

## Guidelines
- Under 200 lines per document
- Be specific - reference actual milestone numbers and design doc sections
- Include the version tag in every suggested backlog item
- Flag any dependencies between suggested items
- Note any items that need an EXP (exploration/investigation) before implementation
- Don't suggest items that already exist in the backlog

## When Complete
git add comms/outbox/exploration/backlog-gap-analysis/
git commit -m "exploration: backlog-gap-analysis complete"
