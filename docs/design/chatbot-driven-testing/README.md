# Chatbot-Driven Testing

This folder captures a high-level design direction for testing Stoat and Ferret through a general-purpose chatbot such as ChatGPT or Claude, with a preference for local CLI/operator workflows over a custom MCP server layer.

The working assumption is:

- Stoat and Ferret's existing REST API, OpenAPI schema, WebSocket events, and GUI are the primary automation surface.
- A local chatbot operator such as Claude Code CLI or Codex local/CLI can act as the first AI testing client.
- A custom MCP server is intentionally deferred unless repeated workflow friction proves that a higher-level tool abstraction is necessary.

## Documents

- `gap-analysis.md`
  High-level analysis of what is already in place for chatbot-driven testing, what is missing, and which gaps matter most.
- `lightweight-design.md`
  A no-MCP-first design for how a local chatbot should interact with Stoat and Ferret once the roadmap is implemented.
- `example-workflow.md`
  A concrete example showing how a local chatbot could drive an end-to-end testing session against the application.

## Conversation Context

These documents were created from a design conversation focused on the future state of Stoat and Ferret after the current roadmap is implemented. The goal was not to redesign the product from scratch, but to answer:

1. What becomes possible once the roadmap is complete?
2. Can a chatbot such as Claude or ChatGPT test and operate the application without a dedicated MCP server?
3. What gaps remain for that use case?

The conclusion of the discussion was:

- chatbot-driven testing is already aligned with the system architecture
- a no-MCP-first approach is sensible
- the main missing pieces are workflow ergonomics, reliability hardening, persistence consistency, and agent-oriented documentation rather than a missing foundational integration layer

## Key Grounding Artifacts

Primary project grounding used for this design set:

- [`01-roadmap.md`](/Users/grant/Documents/projects/stoat-and-ferret/docs/design/01-roadmap.md)
- [`02-architecture.md`](/Users/grant/Documents/projects/stoat-and-ferret/docs/design/02-architecture.md)
- [`05-api-specification.md`](/Users/grant/Documents/projects/stoat-and-ferret/docs/design/05-api-specification.md)
- [`07-quality-architecture.md`](/Users/grant/Documents/projects/stoat-and-ferret/docs/design/07-quality-architecture.md)
- [`08-gui-architecture.md`](/Users/grant/Documents/projects/stoat-and-ferret/docs/design/08-gui-architecture.md)
- [`CHANGELOG.md`](/Users/grant/Documents/projects/stoat-and-ferret/CHANGELOG.md)
- [`app.py`](/Users/grant/Documents/projects/stoat-and-ferret/src/stoat_ferret/api/app.py)
- [`effects.py`](/Users/grant/Documents/projects/stoat-and-ferret/src/stoat_ferret/api/routers/effects.py)
- [`render.py`](/Users/grant/Documents/projects/stoat-and-ferret/src/stoat_ferret/api/routers/render.py)
- [`preview.py`](/Users/grant/Documents/projects/stoat-and-ferret/src/stoat_ferret/api/routers/preview.py)

Companion auto-dev planning and version-grounding used to understand implementation stage:

- [`plan.md`](/Users/grant/Documents/projects/auto-dev-projects/stoat-and-ferret/docs/auto-dev/plan.md)
- [`BACKLOG.md`](/Users/grant/Documents/projects/auto-dev-projects/stoat-and-ferret/docs/auto-dev/BACKLOG.md)
- [`README.md`](/Users/grant/Documents/projects/auto-dev-projects/stoat-and-ferret/docs/auto-dev/README.md)
- [`logical-design.md`](/Users/grant/Documents/projects/auto-dev-projects/stoat-and-ferret/comms/outbox/versions/design/v033/005-logical-design/logical-design.md)
- [`README.md`](/Users/grant/Documents/projects/auto-dev-projects/stoat-and-ferret/comms/outbox/versions/retrospective/v032/005-architecture/README.md)
- [`README.md`](/Users/grant/Documents/projects/auto-dev-projects/stoat-and-ferret/comms/outbox/versions/retrospective/v032/004c-tool-usage/README.md)
- [`README.md`](/Users/grant/Documents/projects/auto-dev-projects/stoat-and-ferret/comms/outbox/versions/retrospective/v032/006-learnings/README.md)
- [`learnings-detail.md`](/Users/grant/Documents/projects/auto-dev-projects/stoat-and-ferret/comms/outbox/versions/retrospective/v032/006-learnings/learnings-detail.md)

## Current Stage Summary

Based on the roadmap, main repo, and companion version docs:

- the platform is already strongly API-first and AI-friendly
- preview, proxy, theater mode, versioning, effects, composition, and render surfaces are largely implemented
- render quality, reliability, and documentation are still being closed out

That makes chatbot-driven testing a near-term integration and workflow problem, not a greenfield architecture problem.
