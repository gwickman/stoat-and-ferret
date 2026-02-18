# Task 005: Context Synthesis

Read AGENTS.md first and follow all instructions there.

## Objective

Create the highest-level C4 documentation: system context. Identify personas, document system features, map user journeys, and catalog external dependencies. This document should be understandable by non-technical stakeholders.

## Context

C4 architecture documentation generation for `${PROJECT}` version `${VERSION}`.
- Container documentation is complete in `docs/C4-Documentation/c4-container.md`
- Component documentation is in `docs/C4-Documentation/c4-component.md`
- This task creates the system-level view

## Tasks

### 1. Gather System Documentation

Read these sources to understand the system's purpose and users:

**Required reads:**
- `docs/C4-Documentation/c4-container.md` — what runs and how
- `docs/C4-Documentation/c4-component.md` — what the system is made of
- `README.md` (project root) — stated purpose and usage

**Additional sources (read if they exist):**
- `docs/ARCHITECTURE.md` or similar
- `docs/auto-dev/PLAN.md` — project direction and goals
- Any `docs/*.md` files that describe the system
- API documentation or usage guides

### 2. Analyze Test Files for Behavior

Scan test directories to understand what the system actually does:

```
tests/ or test/ or __tests__/
spec/ or specs/
```

Test names and descriptions reveal:
- Features the system provides ("test_user_can_login", "test_payment_processing")
- Edge cases and constraints ("test_rejects_invalid_token")
- Integration points ("test_sends_email_notification")

Extract a feature list from test names — this is often more accurate than README claims.

### 3. Identify Personas

**Human users:**
- Who uses this system directly? (end users, admins, developers, operators)
- What roles do they have?
- What are their goals?

**Programmatic users:**
- What external systems call this system's APIs?
- What CI/CD pipelines interact with it?
- What monitoring or automation tools connect to it?

Identify at LEAST 3 personas. Consider these categories: end users (human consumers of the system), programmatic users (other systems, CLI tools, agents that interact with the system), maintainers (developers, CI systems, automation tools that modify the system). If an automation tool like auto-dev-mcp or CI is a significant actor, give it its own persona.

**If unclear from docs:** Infer from API design, authentication mechanisms, and test fixtures.

### 4. Map System Features

For each significant capability the system provides:
- Name it clearly
- Describe what it does (one sentence)
- Identify which personas use it
- Note which containers/components implement it

### 5. Create User Journeys

For each key feature × persona combination, document the step-by-step journey:

```markdown
### [Feature] — [Persona] Journey

1. **[Action]**: [Description of what happens]
2. **[Action]**: [System response or next step]
3. **[Action]**: [Completion or outcome]
```

For programmatic users, document the integration journey:

```markdown
### [External System] Integration Journey

1. **Authenticate**: System sends API key in header
2. **Request**: POST /api/resource with payload
3. **Process**: System validates and processes request
4. **Respond**: Returns result with status code
```

Create at LEAST one user journey per persona. For library projects, include a "Library Integration" journey showing how a consumer adds and uses the dependency. For projects with automation, include an "Automated Development" journey showing the CI/auto-dev workflow.

### 6. Catalog External Dependencies

Everything outside the system boundary:
- Third-party APIs the system calls
- Databases (if managed externally)
- Message brokers
- Auth providers (OAuth, SAML, etc.)
- Cloud services (S3, SQS, Lambda, etc.)
- Monitoring/logging services

### 7. Create Context Documentation

Create `docs/C4-Documentation/c4-context.md`:

```markdown
# C4 Context Level: System Context

## System Overview

### Short Description
[One sentence: what this system does]

### Long Description
[2-3 paragraphs: purpose, capabilities, problems solved, who it serves]

## System Context Diagram

C4Context
    title System Context Diagram for [System Name]
    Person(persona1, "[Name]", "[Description]")
    Person(persona2, "[Name]", "[Description]")
    System(system, "[System Name]", "[What it does]")
    System_Ext(ext1, "[External System]", "[What it provides]")
    SystemDb_Ext(extDb, "[Database]", "[What it stores]")
    Rel(persona1, system, "[Uses for what]")
    Rel(system, ext1, "[Why]", "[Protocol]")

## Personas

### [Persona Name]
- **Type**: Human User | Programmatic User | External System
- **Description**: [Who they are, what they need]
- **Goals**: [What they want to achieve]
- **Key Features Used**: [List]

## System Features

| Feature | Description | Personas | Components |
|---------|-------------|----------|------------|
| [Name] | [What it does] | [Who uses it] | [What implements it] |

## User Journeys

### [Feature] — [Persona] Journey
1. ...
2. ...

## External Systems and Dependencies

### [System Name]
- **Type**: [Database / API / Service / Queue / etc.]
- **Description**: [What it provides]
- **Integration**: [Protocol and method]
- **Purpose**: [Why the system depends on it]

## Related Documentation
- [Container Architecture](./c4-container.md)
- [Component Architecture](./c4-component.md)
```

## Output Requirements

Save outputs to `comms/outbox/exploration/c4-${VERSION}-005-context/`:

### README.md (required)

First paragraph: Summary — persona count, feature count, key system purpose.

Then:
- **System Purpose:** one-sentence summary
- **Personas Identified:** count with list
- **Features Documented:** count with list
- **User Journeys Created:** count
- **External Dependencies:** count with list
- **Sources Used:** which documents informed this analysis

### Context file

`docs/C4-Documentation/c4-context.md` written directly.

## Allowed MCP Tools

- `read_document` (file creation uses Claude Code's native file system capabilities)
- `list_backlog_items` (to understand planned features and system direction)

## Guidelines

- **Stakeholder-friendly language** — avoid jargon; a product manager should understand this
- **Focus on people and systems, not technology** — C4 context level deliberately excludes tech details
- **User journeys should be concrete** — not abstract workflows but specific step sequences
- **Verify journeys against code** — confirm each step in a user journey actually works by checking route definitions, handler implementations, or test assertions, rather than describing intended behavior
- **Test-driven feature discovery** — test names are often the most honest feature list
- **Don't invent personas** — if you can only identify one user type, that's fine
- **Qualify deployment status in user journeys** — when writing user journeys, cross-reference the container doc for deployment status. If a package is not published or a service is not deployed, qualify installation/access steps accordingly (e.g., "after publishing" or "via local installation"). Do not imply public availability unless the container doc confirms it.
- **External systems must be real** — infer from imports, configs, and API calls, not speculation
- **Keep under 200 lines** — this is the highest-level, most accessible C4 document; brevity is a feature
- Do NOT commit — the master prompt handles commits
