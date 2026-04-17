# Lightweight Design - Local Chatbot Testing Without MCP

## Summary

This design describes a no-MCP-first approach for testing Stoat and Ferret through a local chatbot such as Claude Code CLI or Codex local/CLI.

The design goal is to use the existing system architecture as-is:

- REST API for control
- OpenAPI and effect discovery for capability discovery
- WebSocket events for progress and state
- GUI for human-verifiable surfaces

The chatbot is treated as an external operator running locally on the same machine as the application.

## Design Principles

### 1. API-First, Not UI-First

The chatbot should prefer REST and WebSocket integration over browser-driven interaction.

Browser automation remains useful for:

- GUI regression validation
- visual confirmation
- user-journey testing

But the main control path should remain the structured backend API.

### 2. No New Integration Layer by Default

Do not introduce an MCP server or custom tool protocol unless repeated testing shows that the chatbot is consistently burdened by low-level orchestration.

Instead, use:

- existing OpenAPI/API documentation
- a small set of local helper commands or scripts
- lightweight workflow documentation

### 3. Event-Driven Coordination

The chatbot should subscribe to WebSocket events or consume equivalent surfaced state wherever possible.

Polling should be fallback behavior only.

### 4. Keep Human Oversight Easy

The system should remain inspectable by a human while the chatbot operates it. The dashboard, timeline, preview, Theater Mode, and render page remain important companion surfaces during testing.

## Proposed Local Testing Model

### Actor Model

There are three actors:

- **Application**
  Stoat and Ferret backend + frontend
- **Chatbot Operator**
  Claude Code CLI, Codex CLI, or similar local assistant
- **Human Supervisor**
  Observes outputs, adjusts prompts, and reviews failures

### Chatbot Responsibilities

The chatbot should be able to:

- inspect the OpenAPI surface
- discover effects and parameter schemas
- create and manipulate projects
- start previews and renders
- monitor WebSocket progress
- summarize failures and likely causes
- optionally drive the browser for final visual checks

### Human Responsibilities

The human should:

- define the testing goal
- approve destructive or expensive operations if needed
- inspect final outputs and visual quality
- decide whether repeated friction justifies higher-level abstractions

## Preferred Interface Stack

### Primary

- REST endpoints under `/api/v1`
- OpenAPI schema for discovery
- WebSocket `/ws`

### Secondary

- GUI pages for observation and validation
- existing test harnesses, smoke tests, and UAT journeys

### Optional Lightweight Additions

If needed, add only thin helpers such as:

- a local script to start backend + frontend + seed sample media
- a script to dump recent WebSocket events
- a helper that waits for a render or preview to reach a terminal state
- an agent playbook document with common command sequences

These helpers should wrap existing API behavior, not replace it with a parallel abstraction model.

## Suggested Workflow Contract

For a local chatbot, the preferred operating sequence is:

1. Read system capability context.
2. Check health and dependency availability.
3. Discover available resources and project state.
4. Perform task-specific API mutations.
5. Monitor progress through WebSocket events.
6. Validate outputs through API, files, and optionally GUI surfaces.
7. Summarize result, failures, and next steps.

## Minimal Supporting Artifacts To Add

To make this approach practical without MCP, the project should eventually provide:

### 1. Agent Operator Guide

A short document that includes:

- endpoint groups and their intended use
- canonical multi-step workflows
- typical failure recovery patterns
- when to prefer API vs GUI validation

### 2. Prompt Recipes

Examples such as:

- "Scan this folder and build a test project"
- "Apply three candidate effects and show me previews"
- "Run a render and summarize any failure"

### 3. Event Vocabulary Reference

A compact reference for important WebSocket events:

- render progress
- preview status
- proxy readiness
- AI action display events

### 4. Sample Seeded Test Workflow

One known-good project and media set that the chatbot can use for repeatable validation.

## Decision Rule For When To Add MCP Later

An MCP server becomes justified only if one or more of these become recurring pain points:

- the chatbot repeatedly needs the same multi-call orchestration
- prompt-only coordination becomes too brittle
- permissions and guardrails need to be enforced at a higher level
- multiple users need a simpler task-oriented interface than raw API calls
- the team wants a stable tool contract independent of backend route details

Until those are true in practice, local chatbot plus API remains the better tradeoff.

## Expected Outcome

If the roadmap is fully implemented and the key reliability gaps are closed, this no-MCP-first design should support:

- internal exploratory testing
- guided end-to-end validation
- regression testing assistance
- AI-assisted project setup and export checks
- rapid prototyping of future conversational editing flows

## Bottom Line

The best near-term design is:

- chatbot as local operator
- Stoat and Ferret API as the control plane
- WebSocket events as the feedback plane
- GUI as the verification plane
- helper docs/scripts as the ergonomics layer

This approach validates real usage before committing to a dedicated MCP abstraction.
