# Gap Analysis - Chatbot-Driven Testing

## Summary

Stoat and Ferret is already architecturally well aligned with chatbot-driven testing. The backend is broad, structured, and observable. The frontend exposes useful state for human verification. The largest remaining gaps are not basic automation capability, but reliability, ergonomics, and agent-facing workflow support.

The key conclusion is:

- a local chatbot can plausibly test the application through the existing API and GUI model
- a dedicated MCP server is not the first missing piece
- the most important gaps are higher-level orchestration affordances and hardening of supporting systems

## What Already Exists

### 1. Agent-Friendly Control Surface

The project already has the core ingredients a chatbot needs:

- a FastAPI REST API with structured schemas
- OpenAPI generation for discoverability
- explicit effect discovery metadata and AI hints
- resource-oriented endpoints for videos, projects, clips, timeline, preview, render, versions, and batch flows
- transparent FFmpeg/filter outputs for debugging

This means a chatbot does not need brittle UI scraping as its primary interface.

### 2. Runtime Observability

The system already supports event-driven feedback:

- WebSocket updates for scans, preview state, proxy readiness, health, render queue changes, and render progress
- health and metrics endpoints
- structured logging and correlation support

This is important because chatbot testing works much better when the agent can observe state transitions instead of guessing or polling blindly.

### 3. Human-Visible Verification Surfaces

The GUI already provides useful observation points for a chatbot-assisted tester:

- dashboard and health surfaces
- effects workshop with filter previews
- timeline page
- preview page with Theater Mode
- render page and render job cards

That gives the agent both machine-readable and human-readable validation targets.

## Major Gaps

### Gap 1. No High-Level Agent Workflow Layer

The API is broad, but still fairly low-level. A chatbot can call it directly, but many real tasks require a chain of coordinated calls and event handling.

Examples:

- "Create a montage from the newest five clips"
- "Try three transition styles and compare results"
- "Render this project, retry if the first encoder fails, then summarize the outcome"

Today, a general chatbot can do this only by improvising orchestration logic. That is workable for internal testing, but not ideal.

Why it matters:

- increases prompt complexity
- makes behavior less repeatable
- pushes too much reasoning burden into the chat session

### Gap 2. Missing Agent-Facing Workflow Documentation

The project has API docs, design docs, and quality docs, but not yet a compact "AI operator guide."

Missing items include:

- canonical API sequences for common tasks
- preferred ordering of preview, render, and verification operations
- prompt recipes for chatbots
- troubleshooting guidance aimed at an agent operator

Why it matters:

- the chatbot can discover the API, but still lacks strong workflow priors
- repeated trial-and-error increases token cost and error rate

### Gap 3. WebSocket Robustness Is Still Important

The companion planning docs already identify WebSocket message-loss hardening as planned work. For chatbot-driven testing, this is a first-order concern.

Why it matters:

- agents depend on event streams for progress and state synchronization
- dropped or late events can cause duplicate actions, false failures, or stale assumptions
- a human can compensate for unreliable eventing; an agent usually cannot

### Gap 4. Persistence Consistency Is Not Fully Closed

The current plan still calls out persistence gaps for proxy, thumbnail, and waveform-related services.

Why it matters:

- chatbot-driven testing often spans multiple actions, pages, or sessions
- if generated artifacts disappear on restart, the agent sees inconsistent behavior
- test reproducibility suffers

### Gap 5. Render Hardening Is Still in Progress

Render infrastructure is clearly implemented, but companion planning documents show that render quality, contract testing, UAT expansion, and metrics cleanup are still active work.

Why it matters:

- chatbot-driven testing depends heavily on render stability
- rendering is one of the highest-value end-to-end validation paths
- partial maturity here will make the agent feel less reliable than the underlying platform actually is

## Recommended Priorities

If the goal is to enable effective local-chatbot testing without MCP, the highest-value gaps to close are:

1. Finish render quality and reliability work already in the plan.
2. Harden WebSocket delivery and shared frontend state handling.
3. Close service persistence gaps for generated assets.
4. Add a small agent-operator guide with canonical workflows.
5. Optionally add a few helper scripts or thin wrappers for common multi-step operations.

## What Is Not Yet a Priority Gap

A custom MCP server is not the highest-priority gap right now.

Reasons:

- the API is already strong enough to serve as the automation surface
- the main friction is workflow packaging, not missing raw capability
- adding MCP now would create another interface to maintain before workflow pain is validated

## Bottom Line

Stoat and Ferret already has most of the architecture needed for chatbot-driven testing. The remaining work is mainly:

- hardening
- workflow simplification
- persistence cleanup
- agent-oriented guidance

That makes the system a strong candidate for a no-MCP-first approach using a local chatbot operator.
