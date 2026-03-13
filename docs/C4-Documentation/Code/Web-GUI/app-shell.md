# C4 Code Level: App Shell & Routing

**Source:** `gui/src/App.tsx`, `gui/src/main.tsx`, `gui/src/components/Shell.tsx`, `gui/src/components/Navigation.tsx`

**Component:** Web GUI

## Purpose

Provides the application entry point, router configuration, shell layout (header/main/footer), and navigation tabs. Establishes the foundational structure for the SPA with dynamic tab discovery and WebSocket connection status.

## Code Elements

### Root Entry Point

- `createRoot()` in `main.tsx` (line 7)
  - Creates React 18 root, wraps app in `BrowserRouter` with `/gui` basename
  - Enables StrictMode for development checks
  - Mounts to `#root` element in HTML

### Routing

- `App()` component in `App.tsx` (line 9)
  - Uses React Router v7 with nested route layout
  - Shell wraps all pages as outlet
  - Routes:
    - `/` → DashboardPage (index)
    - `/library` → LibraryPage
    - `/projects` → ProjectsPage
    - `/effects` → EffectsPage
    - `/timeline` → TimelinePage

### Layout Components

- `Shell()` component in `Shell.tsx` (line 12)
  - Three-section layout: header (navigation + health), main (outlet), footer (status)
  - Initializes WebSocket connection via `useWebSocket()`
  - Applies dark theme styling (bg-gray-950, text-gray-100)
  - Returns: flexbox column with full viewport height

- `Navigation()` component in `Navigation.tsx` (line 18)
  - Discovers available tabs by probing endpoints with HEAD requests
  - Tabs checked: `/health/live`, `/api/v1/videos`, `/api/v1/projects`, `/api/v1/effects`, `/api/v1/compose/presets`
  - Renders `NavLink` for each available tab with active state styling
  - Lazy-loads; re-checks availability on mount only
  - Returns: horizontal nav flex with rounded-top styling

### Helper Functions

- `wsUrl()` in `Shell.tsx` (line 7) and `DashboardPage.tsx` (line 10)
  - Detects HTTPS/HTTP and returns appropriate WebSocket protocol (`wss:` or `ws:`)
  - Uses `window.location` for dynamic host/protocol resolution

## Dependencies

### Internal Dependencies

- `useWebSocket` hook from `hooks/useWebSocket`
- `HealthIndicator` component from `components/HealthIndicator`
- `StatusBar` component from `components/StatusBar`
- Page components: DashboardPage, EffectsPage, LibraryPage, ProjectsPage, TimelinePage

### External Dependencies

- `react`, `react-dom` (React 18, React Router DOM v7)
- `react-router-dom`: `Route`, `Routes`, `Outlet`, `NavLink`, `BrowserRouter`
- Tailwind CSS for styling

## Key Implementation Details

### Navigation Discovery Pattern

The Navigation component uses a capability-checking pattern:
1. On mount, it fetches all tab endpoints with HEAD requests
2. Filters tabs where `res.ok || res.status === 405` (405 = method not allowed, endpoint exists)
3. Caches availability state; doesn't re-check on updates
4. Deselects unavailable tabs from the UI

This allows graceful degradation if certain API features aren't ready.

### WebSocket Initialization

WebSocket is created at the Shell level (parent of all pages) so:
- Single connection shared across all routes
- Activity logged to dashboard regardless of current page
- Remains connected during navigation

### Routing Structure

Uses React Router v7 nested routes:
- Shell is a layout route (always mounted)
- Child routes replace the `<Outlet />` content
- `basename="/gui"` handles deployment under sub-path

## Relationships

```mermaid
---
title: App Shell Architecture
---
classDiagram
    namespace Shell {
        class App {
            +render Routes
        }
        class BrowserRouter {
            +basename="/gui"
        }
        class Shell {
            +useWebSocket()
            +render header, main outlet, footer
        }
        class Navigation {
            +checkAvailableTabs()
            +render NavLinks
        }
        class HealthIndicator {
            +display health status
        }
        class StatusBar {
            +display WS connection
        }
    }
    namespace Pages {
        class DashboardPage
        class LibraryPage
        class ProjectsPage
        class EffectsPage
        class TimelinePage
    }
    BrowserRouter --> App
    App --> Shell
    Shell --> Navigation
    Shell --> HealthIndicator
    Shell --> StatusBar
    Shell --> Pages
    Navigation -.->|HEAD /api/v1/*| Pages
```

## Code Locations

- **App.tsx**: Route definitions and component tree
- **main.tsx**: Root render entry, BrowserRouter setup
- **Shell.tsx**: Layout structure, WebSocket initialization
- **Navigation.tsx**: Tab discovery and rendering logic

