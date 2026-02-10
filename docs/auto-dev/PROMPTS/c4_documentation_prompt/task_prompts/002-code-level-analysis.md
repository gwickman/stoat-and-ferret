# Task 002: Code-Level Analysis (Batch ${BATCH_NUMBER})

Read AGENTS.md first and follow all instructions there.

## Objective

Analyze the source code in each assigned directory and produce C4 Code-level documentation files. This is one of multiple parallel batches — this batch processes a specific subset of directories.

## Context

C4 architecture documentation generation for `${PROJECT}` version `${VERSION}`.
- **Batch:** ${BATCH_NUMBER} of ${BATCH_COUNT}
- **Directories in this batch:** (listed below)

## Directories to Process

Process these directories in order (deepest first):

${BATCH_DIRECTORIES}

## Tasks

For EACH directory in the list above:

### 1. Analyze Code Structure

Read all source code files in the directory. For each file:
- Identify the programming language and paradigm (OOP, FP, procedural, mixed)
- Extract all public functions/methods with complete signatures
- Extract all classes/modules with their hierarchies
- Identify imports, dependencies, and relationships

### 2. Create C4 Code-Level Document

Produce a markdown file following this structure:

```markdown
# C4 Code Level: [Descriptive Name for Directory]

## Overview
- **Name**: [Descriptive name]
- **Description**: [What this code does — one sentence]
- **Location**: [Relative path from repo root]
- **Language**: [Primary language(s)]
- **Purpose**: [What this code accomplishes]
- **Parent Component**: [To be assigned in Task 003]

## Code Elements

### Functions/Methods

- `functionName(param1: Type, param2: Type): ReturnType`
  - Description: [What it does]
  - Location: [file:line]
  - Dependencies: [what it calls/imports]

### Classes/Modules

- `ClassName`
  - Description: [What it does]
  - Location: [file path]
  - Methods: [list with signatures]
  - Dependencies: [what it depends on]

## Dependencies

### Internal Dependencies
- [Other project modules this code imports]

### External Dependencies
- [Libraries, frameworks, external services]

## Relationships

[Mermaid diagram if there are 3+ elements with non-trivial relationships]

Choose diagram type based on the programming paradigm:

**OOP (classes, interfaces, inheritance) → classDiagram:**
\`\`\`mermaid
---
title: Code Diagram for [Directory Name]
---
classDiagram
    class ClassName {
        +attribute1 Type
        +method1(param Type) ReturnType
    }
    class InterfaceName {
        <<interface>>
        +requiredMethod() ReturnType
    }
    ClassName ..|> InterfaceName : implements
    ClassName --> OtherClass : uses
\`\`\`

**FP/pipelines (data transformations, function composition) → flowchart:**
\`\`\`mermaid
---
title: Data Pipeline for [Directory Name]
---
flowchart LR
    subgraph Input
        A[readFile]
    end
    subgraph Transform
        B[parseJSON] --> C[validate] --> D[normalize]
    end
    subgraph Output
        E[writeFile]
    end
    A -->|raw| B
    D -->|clean data| E
\`\`\`

**Modules with exports (FP/procedural) → classDiagram with <<module>>:**
\`\`\`mermaid
classDiagram
    class validators {
        <<module>>
        +validateInput(data) Result
        +sanitize(input) string
    }
    class transformers {
        <<module>>
        +normalize(data) NormalizedData
        +aggregate(items) Summary
    }
    transformers --> validators : uses
\`\`\`

**Function dependency graph (procedural/mixed) → flowchart TB:**
\`\`\`mermaid
flowchart TB
    subgraph Public API
        processData
        exportReport
    end
    subgraph Internal
        validate
        transform
    end
    processData --> validate --> transform
    exportReport --> processData
\`\`\`

**Decision table:**
| Code Style | Diagram | When |
|-----------|---------|------|
| OOP (classes, interfaces) | `classDiagram` | Inheritance, composition, interface implementation |
| FP (pure functions, pipelines) | `flowchart LR` | Data transformations and function composition |
| FP (modules with exports) | `classDiagram` + `<<module>>` | Module structure and dependencies |
| Procedural (structs + functions) | `flowchart TB` | Call graphs and function dependencies |
| Mixed | Best fit for dominant pattern | Use multiple diagrams if needed |

Every c4-code-*.md file MUST include a Mermaid diagram. For simple modules with few elements, use a classDiagram showing the module's exported interface. Do NOT skip diagrams — consistency across all code-level docs is required.
```

### 3. Save to C4-Documentation

Save each document as:
```
docs/C4-Documentation/c4-code-[sanitized-directory-name].md
```

**Sanitization rules:**
- Replace `/` and `\` with `-`
- Remove leading `src-` if it results in a clear name
- Remove special characters
- Use lowercase
- Example: `src/handlers/auth` → `c4-code-handlers-auth.md`

## Output Requirements

Save outputs to `comms/outbox/exploration/c4-${VERSION}-002-batch${BATCH_NUMBER}/`:

### README.md (required)

First paragraph: Summary — how many directories processed, any issues encountered.

Then:
- **Directories Processed:** count with list
- **Files Created:** list of c4-code-*.md files created in docs/C4-Documentation/
- **Issues:** any directories that couldn't be fully analyzed (empty dirs, binary-only, etc.)
- **Languages Detected:** summary of languages found

### Per-directory output

Each `c4-code-*.md` file written directly to `docs/C4-Documentation/` (NOT to the exploration output folder).

## Allowed MCP Tools

- `read_document` (file creation uses Claude Code's native file system capabilities)

## Guidelines

- **Include a Parent Component field** set to "TBD" in each code-level doc — Task 003 will update these references during component synthesis
- **Accuracy over completeness** — if you can't determine a return type, say "unknown" rather than guess
- **Complete function signatures** — include all parameters with types where available
- **Keep each code doc under 300 lines** — summarize if a directory has 50+ functions, prioritizing public API and key abstractions
- **Skip test files** unless the directory contains ONLY test files (then document the test structure)
- **For test directories, include:** total test count (number of `it()` or `test()` calls), test file inventory with per-file counts, and coverage summary showing which source functions have test coverage
- **Verified test counts:** When documenting test directories, attempt to get verified test counts by running the project's test command (e.g., `npm test`, `pytest --co -q`, `cargo test -- --list`). If the test command succeeds, use the actual count. If it fails or is unavailable, estimate from the source and note "estimated from source — not verified by execution"
- **Skip generated files** (auto-generated code, compiled output, etc.)
- **Link to source** — use relative paths from repo root for all file references
- Do NOT synthesize components — that's Task 003's job
- Do NOT commit — the master prompt handles commits after all batches complete
