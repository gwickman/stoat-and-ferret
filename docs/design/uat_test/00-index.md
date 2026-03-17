# UAT Design Documents — Index

## Purpose

This directory contains the design documents for stoat-and-ferret's User Acceptance Testing (UAT) framework. The UAT framework fills the gap between existing automated tests (smoke tests, Playwright E2E specs) and real end-user validation by walking through complete user journeys in a real browser against a live application instance.

## When to Run UAT

### Automated (Tier 1 — Headless)

- **On every version closure** as part of the `VERSION_CLOSURE.md` checklist
- Runs headless Playwright against all 7 user journeys
- Produces structured JSON + markdown reports with screenshot evidence
- Flags failures for human Tier 2 review

### Manual (Tier 2 — Headed)

- **When Tier 1 flags issues** that need human visual inspection
- **Before major releases** for final sign-off
- **After GUI-impacting changes** when visual correctness matters
- Developer runs `python scripts/uat_runner.py --headed` locally with a visible browser

## Development Lifecycle Integration

1. Development proceeds normally with unit, smoke, and E2E tests
2. Version work completes and passes CI
3. Tier 1 UAT runs automatically during version closure (headless)
4. If Tier 1 passes: version closure proceeds
5. If Tier 1 fails: developer runs Tier 2 (headed) to diagnose and file bugs

## Document Index

| Document | Description |
|----------|-------------|
| [01-overview.md](./01-overview.md) | Problem statement and motivation — why smoke tests and E2E specs are insufficient |
| [02-architecture.md](./02-architecture.md) | Full technical design: CLI, build/boot sequence, screenshot strategy, report format, two-tier model |
| [03-user-journeys.md](./03-user-journeys.md) | The 7 critical user journeys with step-by-step actions, expected outcomes, and screenshot checkpoints |
| [04-auto-dev-integration.md](./04-auto-dev-integration.md) | How UAT integrates with auto-dev version closure, two-tier model, VERSION_CLOSURE.md updates, limitations |
| [05-dependencies.md](./05-dependencies.md) | New dependencies required, rationale for Python Playwright over TypeScript, risk mitigations |
