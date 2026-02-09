# Requirements - 001: Application Shell

## Goal

Build the application shell with navigation tabs, health indicator, status bar, progressive tab disclosure, and WebSocket reconnection via a `useWebSocket` custom hook.

## Background

M1.10 specifies an application shell with navigation tabs, status bar, and health indicator, but no frontend components exist. The shell is the frame that hosts all other GUI panels (library browser, project manager, dashboard). Without it, individual components have no layout structure or navigation context. The frontend project and WebSocket endpoint are established in Theme 01.

**Backlog Item:** BL-030

## Functional Requirements

**FR-001: Tab navigation**
Navigation between Dashboard, Library, and Projects tabs with URL routing via React Router.
- AC: Clicking each tab navigates to the correct URL and renders the corresponding panel

**FR-002: Health indicator**
Health indicator polls `/health/ready` and displays green (all healthy), yellow (degraded), or red (unhealthy) status.
- AC: Health indicator shows correct color based on `/health/ready` response

**FR-003: Status bar**
Status bar displays WebSocket connection state (connected, disconnected, reconnecting).
- AC: Status bar reflects current WebSocket connection status

**FR-004: Progressive tab disclosure**
Only show tabs for features whose backends are available. Check backend availability at startup.
- AC: Tabs are shown/hidden based on backend feature availability

**FR-005: WebSocket reconnection hook**
Implement `useWebSocket` custom hook with auto-reconnect using exponential backoff. Handles connect, disconnect, and reconnect lifecycle.
- AC: WebSocket automatically reconnects after disconnect with increasing backoff delay

**FR-006: Layout structure**
Provide a layout shell with header (navigation + health), main content area (panel rendering), and footer (status bar).
- AC: Layout renders with header, content, and footer sections

## Non-Functional Requirements

**NFR-001: Navigation responsiveness**
Tab switching renders the new panel within 100ms (no full page reload).
- Metric: Client-side routing transition < 100ms

**NFR-002: Health polling interval**
Health indicator polls at a reasonable interval (e.g., 30s) to avoid excessive API load.
- Metric: Health poll interval >= 15s

## Out of Scope

- Responsive/mobile layout (desktop-first for local app)
- Theme switching (light/dark mode)
- User preferences or settings panel
- Keyboard shortcuts for navigation

## Test Requirements

| Category | Requirements |
|----------|-------------|
| Unit tests (Vitest) | Navigation component renders all tabs; URL routing maps to correct panels; health indicator renders green/yellow/red based on mock API response; status bar shows WebSocket state |
| Integration tests | None (frontend-only; integration covered by E2E in Theme 04) |

## Reference

See `comms/outbox/versions/design/v005/004-research/` for supporting evidence.