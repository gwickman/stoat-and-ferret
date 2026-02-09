# Implementation Plan - 001: Application Shell

## Overview

Build the application shell with React Router navigation, health indicator polling `/health/ready`, status bar showing WebSocket connection state, and a `useWebSocket` custom hook with auto-reconnect. This provides the layout frame for all GUI panels.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `gui/src/App.tsx` | Modify | Replace default Vite content with shell layout and router |
| `gui/src/components/Shell.tsx` | Create | Main shell layout (header, content, footer) |
| `gui/src/components/Navigation.tsx` | Create | Tab navigation component |
| `gui/src/components/HealthIndicator.tsx` | Create | Health status indicator (green/yellow/red) |
| `gui/src/components/StatusBar.tsx` | Create | WebSocket connection status bar |
| `gui/src/hooks/useWebSocket.ts` | Create | WebSocket hook with auto-reconnect |
| `gui/src/hooks/useHealth.ts` | Create | Health polling hook |
| `gui/src/pages/DashboardPage.tsx` | Create | Placeholder dashboard page |
| `gui/src/pages/LibraryPage.tsx` | Create | Placeholder library page |
| `gui/src/pages/ProjectsPage.tsx` | Create | Placeholder projects page |
| `gui/package.json` | Modify | Add react-router-dom dependency |
| `gui/src/components/__tests__/Shell.test.tsx` | Create | Shell component tests |
| `gui/src/components/__tests__/Navigation.test.tsx` | Create | Navigation component tests |
| `gui/src/hooks/__tests__/useWebSocket.test.ts` | Create | WebSocket hook tests |

## Implementation Stages

### Stage 1: Shell Layout and Router

1. Install `react-router-dom`
2. Create `Shell.tsx` with header (navigation + health), main content area, and footer (status bar)
3. Configure `BrowserRouter` with `basename="/gui"` in `App.tsx`
4. Create route definitions: `/` (Dashboard), `/library` (Library), `/projects` (Projects)
5. Create placeholder page components for each route

**Verification:**
```bash
cd gui && npm run build
cd gui && npx vitest run
```

### Stage 2: Navigation Component

1. Create `Navigation.tsx` with tab buttons for Dashboard, Library, Projects
2. Use `NavLink` from react-router-dom for active tab highlighting
3. Implement progressive tab disclosure: check backend availability at startup, hide unavailable tabs
4. Add unit tests for tab rendering and active state

**Verification:**
```bash
cd gui && npx vitest run
```

### Stage 3: Health Indicator and WebSocket Hook

1. Create `useHealth` hook that polls `/health/ready` at configurable interval (default 30s)
2. Create `HealthIndicator.tsx` rendering green/yellow/red based on health response
3. Create `useWebSocket` hook:
   - Connect to `/ws` endpoint
   - Handle `onopen`, `onclose`, `onerror`, `onmessage` events
   - Auto-reconnect with exponential backoff (1s, 2s, 4s, 8s, max 30s)
   - Expose connection state: `connected`, `disconnected`, `reconnecting`
4. Create `StatusBar.tsx` displaying WebSocket connection state
5. Add unit tests for hooks and components

**Verification:**
```bash
cd gui && npx vitest run
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest tests/
```

## Test Infrastructure Updates

- Vitest tests with mocked `fetch` for health API
- Vitest tests with mocked WebSocket for connection hook
- React Testing Library for component rendering tests

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
cd gui && npx vitest run
```

## Risks

- **R-3 (WebSocket stability):** Auto-reconnect with exponential backoff handles disconnections. Local app minimizes network issues.

See `comms/outbox/versions/design/v005/006-critical-thinking/risk-assessment.md`.

## Commit Message

```
feat: build application shell with navigation and WebSocket support

- Create shell layout with header, content area, and status bar
- Add React Router navigation between Dashboard, Library, Projects
- Implement health indicator polling /health/ready
- Add useWebSocket hook with auto-reconnect and exponential backoff
- Add progressive tab disclosure based on backend availability

Implements BL-030
```