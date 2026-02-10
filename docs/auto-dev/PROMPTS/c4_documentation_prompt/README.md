# C4 Documentation Prompt

Orchestrated C4 architecture documentation generation using the exploration framework.

## Overview

Generates comprehensive C4 architecture documentation (Context, Container, Component, Code levels) with Mermaid diagrams. Designed for scalability via parallel explorations and delta-mode updates.

## Structure

```
c4_documentation_prompt/
├── 000-master-prompt.md          # Orchestrator — run this
└── task_prompts/
    ├── 001-discovery-and-planning.md   # Discover directories, plan batches
    ├── 002-code-level-analysis.md      # Code analysis (parallelized per batch)
    ├── 003-component-synthesis.md      # Synthesize into components
    ├── 004-container-synthesis.md      # Map to deployment containers
    ├── 005-context-synthesis.md        # System context, personas, journeys
    └── 006-finalization.md             # README, validation, cleanup
```

## Modes

| Mode | When to Use | What It Does |
|------|-------------|--------------|
| `full` | First generation, major refactors | Processes all source directories |
| `delta` | After a version run | Only reprocesses directories with changes |
| `auto` | Default — detects which to use | Checks for existing docs, uses delta if possible |

## Execution Flow

```
001 Discovery ──→ 002 Code (parallel batches) ──→ 003 Components ──→ 004 Containers ──→ 005 Context ──→ 006 Finalize
     │                    │ │ │
     │                    ▼ ▼ ▼
     │               (up to 6 parallel explorations)
     │
     └── Determines full/delta mode and batch groupings
```

## Integration with Version Lifecycle

**During version design:** The design prompt (Task 001) checks C4 doc currency.
**During retrospective:** The retro prompt (Task 005) detects architecture drift.
**When drift detected:** Run this prompt in `delta` mode to update documentation.

## Usage

1. Set PROJECT, VERSION, and MODE in `000-master-prompt.md`
2. Run the master prompt via chatbot orchestration
3. Monitor parallel code-level batches
4. Final output lands in `docs/C4-Documentation/`

## Replaces

This prompt set replaces `c4-regeneration.md` (the single-file plugin-based approach).
