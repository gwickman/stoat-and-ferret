# Smoke Test Design

**Project:** stoat-and-ferret — AI-driven video editor with hybrid Python/Rust architecture

## Overview

The smoke test suite provides API-level end-to-end testing that exercises the full backend stack: FastAPI endpoints, Python services, Rust core (via PyO3), SQLite database, and real video files. It fills a critical gap in the project's quality gates — while unit and integration tests validate individual layers in isolation, no existing tests exercise the full request lifecycle from HTTP client through to database persistence and Rust-powered validation.

## Relationship to Existing Quality Gates

The project has comprehensive per-layer quality gates:

| Layer | Tool | What it covers |
|-------|------|----------------|
| Python lint/format | ruff | Code style, import ordering, common bugs |
| Python types | mypy | Static type checking across the Python layer |
| Python tests | pytest | Unit + integration tests with mocked dependencies |
| Frontend types | TypeScript (`tsc`) | Static type checking for React/TypeScript |
| Frontend tests | Vitest | Component and hook unit tests |
| Rust lint | clippy | Rust-specific linting |
| Rust tests | cargo test + proptest | Pure function testing, property-based testing |

**The gap:** None of these test the full stack together. A broken database migration, a misconfigured PyO3 binding, or a schema mismatch between API and Rust core would pass all existing tests but fail in production.

Smoke tests close this gap by making real HTTP requests to a real FastAPI app backed by a real SQLite database and real Rust core, scanning real video files.

## Two-Phase Strategy

### Phase 1: Python + httpx (API-level) — Current Design

- **Technology:** `httpx.AsyncClient` with `ASGITransport`, running in-process via pytest
- **Scope:** All implemented API endpoints exercised through 12 use cases
- **Speed:** Sub-10 seconds for the full suite
- **Dependencies:** Zero new dependencies (httpx and pytest-asyncio already installed)
- **Confidence:** Validates full backend stack including Rust core; does not test browser rendering

### Phase 2: Playwright (browser E2E) — Future

- **Technology:** Playwright with `@playwright/test` runner
- **Scope:** 9 browser-level use cases exercising the React GUI
- **When:** After GUI feature set stabilizes (Phase 3+ roadmap completion)
- **Why Playwright:** Already in project tech plan, `data-testid` attributes present in all 27 React components, native WebSocket testing support, multi-browser coverage

## Current Status

Phase 1 is **designed but not yet built**. This document set contains the complete specification for implementation.

## Files in This Folder

| File | Contents |
|------|----------|
| [01-background.md](./01-background.md) | Testing gap analysis, GUI state, phase rationale, video metadata |
| [02-infrastructure.md](./02-infrastructure.md) | Test file layout, conftest.py design, fixtures, helpers |
| [03-test-cases.md](./03-test-cases.md) | All 12 test case specifications with exact HTTP calls and assertions |
| [04-ci-integration.md](./04-ci-integration.md) | GitHub Actions job, timeout strategy, flakiness mitigation |
| [05-maintenance.md](./05-maintenance.md) | Trigger table, sync strategy, impact assessment checks |
| [06-phase2-playwright.md](./06-phase2-playwright.md) | Phase 2 Playwright design, 9 use cases, CI job |
