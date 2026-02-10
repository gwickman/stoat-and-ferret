# Task 002: Code-Level Analysis (Batch 3)

Read AGENTS.md first and follow all instructions there.

## Objective

Analyze the source code in each assigned directory and produce C4 Code-level documentation files. This is one of multiple parallel batches — this batch processes a specific subset of directories.

## Context

C4 architecture documentation generation for `stoat-and-ferret` version `v005`.
- **Batch:** 3 of 4
- **Directories in this batch:** (listed below)

## Directories to Process

Process these directories in order (deepest first):

- gui/src/components/__tests__
- gui/src/components
- gui/src/hooks/__tests__
- gui/src/hooks
- gui/src/pages
- gui/src/stores
- gui/src

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

[Mermaid diagram — REQUIRED for every file]

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
- Example: `gui/src/components` → `c4-code-gui-components.md`

## Output Requirements

Save outputs to `comms/outbox/exploration/c4-v005-002-batch3/`:

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

- **Accuracy over completeness** — if you can't determine a return type, say "unknown" rather than guess
- **Complete function signatures** — include all parameters with types where available
- **Keep each code doc under 300 lines** — summarize if a directory has 50+ functions, prioritizing public API and key abstractions
- **Skip test files** unless the directory contains ONLY test files (then document the test structure)
- **For test directories, include:** total test count (number of `it()` or `test()` calls), test file inventory with per-file counts, and coverage summary showing which source functions have test coverage
- **Skip generated files** (auto-generated code, compiled output, etc.)
- **Link to source** — use relative paths from repo root for all file references
- Do NOT synthesize components — that's Task 003's job
- Do NOT commit — the master prompt handles commits after all batches complete