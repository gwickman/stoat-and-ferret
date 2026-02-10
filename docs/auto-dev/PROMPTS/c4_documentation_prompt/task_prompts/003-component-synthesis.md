# Task 003: Component Synthesis

Read AGENTS.md first and follow all instructions there.

## Objective

Read all C4 Code-level documentation files and synthesize them into logical components. Define component boundaries, interfaces, and relationships. Produce component-level documentation with Mermaid C4Component diagrams.

## Context

C4 architecture documentation generation for `${PROJECT}` version `${VERSION}`.
- **Mode:** `${MODE}`
- All `c4-code-*.md` files are now present in `docs/C4-Documentation/`
- This task synthesizes them upward into component-level architecture

## Tasks

### 1. Read All Code-Level Documentation

Read every `docs/C4-Documentation/c4-code-*.md` file. Build a mental model of:
- What each directory does
- How directories relate to each other (shared dependencies, call patterns)
- Natural groupings (domain boundaries, technical boundaries)

### 2. Identify Component Boundaries

Group code-level elements into logical components based on:

**Domain boundaries** (preferred):
- Code that serves the same business capability
- Code that changes together for the same business reasons

**Technical boundaries** (secondary):
- Shared framework usage (all Express handlers, all SQLAlchemy models)
- Layer boundaries (API layer, service layer, data layer)

**Organizational boundaries** (tertiary):
- Module/package boundaries already defined in the codebase
- Explicit namespace or package separation

**Rules:**
- Every `c4-code-*.md` file must belong to exactly one component
- Target 2-8 code-level elements per component. Single-element components are acceptable for standalone modules. Components exceeding 8 elements should be reviewed for possible splitting, but are acceptable when the domain justifies it
- If a directory doesn't fit anywhere, it becomes its own component

### 3. Document Each Component

For each identified component, create `docs/C4-Documentation/c4-component-[name].md`:

```markdown
# C4 Component Level: [Component Name]

## Overview
- **Name**: [Component name]
- **Description**: [What this component does — one sentence]
- **Type**: [Application, Service, Library, Data Access, etc.]
- **Technology**: [Primary technologies]

## Purpose

[2-3 paragraphs: what this component does, what problems it solves, its role in the system]

## Software Features
- [Feature 1]: [Description]
- [Feature 2]: [Description]

## Code Elements

This component contains:
- [c4-code-file-1.md](./c4-code-file-1.md) — [Brief description]
- [c4-code-file-2.md](./c4-code-file-2.md) — [Brief description]

## Interfaces

### [Interface Name]
- **Protocol**: [REST/GraphQL/gRPC/Events/Function calls/etc.]
- **Description**: [What this interface provides]
- **Operations**:
  - `operationName(params): ReturnType` — [Description]

## Dependencies

### Components Used
- [Component Name]: [How and why it's used]

### External Systems
- [System]: [How it's used]

## Component Diagram

C4Component
    title Component Diagram for [Container Name]
    Container_Boundary(container, "[Container Name]") {
        Component(comp1, "[Name]", "[Type]", "[Description]")
        Component(comp2, "[Name]", "[Type]", "[Description]")
    }
    Rel(comp1, comp2, "[Relationship]")
```

### 4. Create Master Component Index

Create `docs/C4-Documentation/c4-component.md`:

```markdown
# C4 Component Level: System Overview

## System Components

| Component | Description | Code Elements | Documentation |
|-----------|-------------|---------------|---------------|
| [Name] | [Description] | N files | [link] |

## Component Relationships

[Mermaid C4Component diagram showing ALL components and their relationships]

## Component-to-Code Mapping

[Table showing which c4-code-*.md files belong to which component]
```

### 5. Delta Mode Consideration

If MODE is `delta`:
- Re-read ALL existing component docs (not just changed ones)
- Identify which components contain changed code-level docs
- Update those components' documentation
- Check if boundary changes are needed (new code might belong to a different component)
- Update the master index

## Output Requirements

Save outputs to `comms/outbox/exploration/c4-${VERSION}-003-components/`:

### README.md (required)

First paragraph: Summary — component count, any boundary decisions that were difficult.

Then:
- **Components Identified:** count with list
- **Code-to-Component Mapping:** which code files went where
- **Boundary Rationale:** brief explanation of grouping decisions
- **Cross-Component Dependencies:** key dependency patterns found
- **Delta Changes (if applicable):** what changed vs previous component structure

### Component files

All `c4-component-*.md` and `c4-component.md` written directly to `docs/C4-Documentation/`.

## Allowed MCP Tools

- `read_document` (file creation uses Claude Code's native file system capabilities)

## Guidelines

- **Logical grouping over mechanical grouping** — don't just group by directory; group by purpose
- **Every code file must be assigned** — no orphans
- **Component names should be meaningful** — "AuthenticationService" not "src-auth-handlers"
- **Interfaces should be concrete** — document actual function signatures, not vague descriptions
- **Keep individual component docs under 200 lines**
- **Master index should fit on one screen** — summary view, not exhaustive detail
- Do NOT map to containers — that's Task 004's job
- Do NOT commit — the master prompt handles commits
