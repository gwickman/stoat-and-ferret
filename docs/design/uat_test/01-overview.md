# 01 — Overview: Why UAT?

## Problem Statement

stoat-and-ferret has a comprehensive test suite — 17 smoke test files, 6 Playwright E2E specs, API unit tests, black box tests, contract tests, security tests, and property tests. CI runs across 3 OS × 3 Python versions with 80% coverage gates. Despite this, **no test walks through the application as a real user would**.

## The End-User Gap

### What Smoke Tests Cover (and Don't)

Smoke tests exercise the full Python → FastAPI → Service → PyO3/Rust → SQLite stack using real databases. They validate use cases UC-01 through UC-12 via `httpx.AsyncClient`, hitting REST endpoints directly.

**What they cannot detect:**
- A button that doesn't trigger the correct API call
- A form that sends malformed parameters
- A loading spinner that never resolves
- A result list that doesn't render returned data
- Layout or rendering regressions

### What Playwright E2E Specs Cover (and Don't)

The 6 existing Playwright specs test individual page loads and UI components: SPA routing, project creation modal, accessibility (WCAG AA via axe-core), navigation, effect UI interactions, and scan workflow UI.

**What they don't do:**
- Walk through multi-step user journeys (scan → browse → create project → add clips → apply effects → view timeline)
- Exercise the app against a real database with real scanned videos (they intercept API responses with canned data)
- Capture screenshot evidence at each step for visual regression
- Produce structured bug reports

### The Consequence

A regression like PR-012 (timeline field data loss after server restart) would pass all existing tests because:
1. Smoke tests verify the API returns correct data — but the GUI might not display it
2. E2E specs verify individual page components work — but don't test multi-step flows that reveal state persistence bugs
3. No test captures what the user actually sees on screen

## What UAT Addresses

The UAT framework fills these 7 specific gaps identified in the test baseline analysis:

| Gap | Description | UAT Coverage |
|-----|-------------|--------------|
| 1 | No end-to-end user journey testing | 7 multi-step journeys covering the complete user workflow |
| 2 | No screenshot evidence or visual regression | Screenshots at every checkpoint, FAIL_ prefix on failures |
| 3 | No real data in browser tests | UAT runs against a live server with real scanned videos and seeded sample data |
| 4 | Smoke tests are API-only | UAT clicks through the GUI as a real user would |
| 5 | No render/export verification | Journey 7 covers the full sample project including rendered output state |
| 6 | No audio workflow coverage in GUI | Noted as future extension once audio UI matures |
| 7 | Theater mode and preview player not testable | Noted as "not testable" in journey scripts rather than failing |
