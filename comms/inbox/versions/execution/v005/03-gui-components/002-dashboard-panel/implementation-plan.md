# Implementation Plan - 002: Dashboard Panel

## Overview

Build the dashboard panel as the landing page with system health cards from `/health/ready`, a real-time activity log subscribing to WebSocket events, and metrics cards from `/metrics`. Auto-refresh keeps data current.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `gui/src/pages/DashboardPage.tsx` | Modify | Replace placeholder with full dashboard implementation |
| `gui/src/components/HealthCards.tsx` | Create | Individual component status cards |
| `gui/src/components/ActivityLog.tsx` | Create | Real-time WebSocket event log |
| `gui/src/components/MetricsCards.tsx` | Create | API metrics display cards |
| `gui/src/hooks/useMetrics.ts` | Create | Metrics polling hook |
| `gui/src/stores/activityStore.ts` | Create | Zustand store for activity log state |
| `gui/src/components/__tests__/HealthCards.test.tsx` | Create | Health cards tests |
| `gui/src/components/__tests__/ActivityLog.test.tsx` | Create | Activity log tests |
| `gui/src/components/__tests__/MetricsCards.test.tsx` | Create | Metrics cards tests |
| `gui/package.json` | Modify | Add zustand dependency |

## Implementation Stages

### Stage 1: Health Cards

1. Install `zustand` for state management
2. Create `HealthCards.tsx` component that displays individual status for Python API, Rust core, and FFmpeg
3. Consume health data from `useHealth` hook (from Feature 001)
4. Render green/yellow/red cards per component

**Verification:**
```bash
cd gui && npx vitest run
```

### Stage 2: Activity Log

1. Create Zustand `activityStore` to manage activity log entries (max 50, FIFO eviction)
2. Create `ActivityLog.tsx` component displaying event type, timestamp, and details
3. Subscribe to WebSocket messages via `useWebSocket` hook from Feature 001
4. Add new events to activity store on WebSocket message receipt

**Verification:**
```bash
cd gui && npx vitest run
```

### Stage 3: Metrics Cards and Auto-Refresh

1. Create `useMetrics` hook that fetches `/metrics` endpoint and parses Prometheus format
2. Create `MetricsCards.tsx` displaying request count and average operation timing
3. Implement auto-refresh: `DashboardPage` re-fetches health and metrics on configurable interval (default 30s)
4. Assemble all components in `DashboardPage.tsx`

**Verification:**
```bash
cd gui && npx vitest run
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest tests/
```

## Test Infrastructure Updates

- Vitest tests with mocked fetch for `/health/ready` and `/metrics`
- Vitest tests with mocked WebSocket events for activity log
- Zustand store tests for FIFO eviction logic

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
cd gui && npx vitest run
```

## Risks

None specific to this feature. Dashboard consumes established infrastructure from Theme 01.

See `comms/outbox/versions/design/v005/006-critical-thinking/risk-assessment.md`.

## Commit Message

```
feat: build dashboard panel with health cards, activity log, and metrics

- Add health cards showing Python, Rust core, FFmpeg status
- Implement real-time activity log via WebSocket events
- Add metrics cards displaying API request count and timing
- Configure auto-refresh on 30s interval with Zustand state

Implements BL-031
```