# Handoff: 001-application-shell

## What Was Built

The application shell provides the layout frame for all GUI panels:
- **Shell component** with header (nav + health), main content area, and footer (status bar)
- **React Router** with basename `/gui` and routes for Dashboard, Library, Projects
- **useWebSocket hook** with auto-reconnect (exponential backoff: 1s, 2s, 4s... max 30s)
- **useHealth hook** polling `/health/ready` every 30s
- **Progressive tab disclosure** - tabs only appear when their backend endpoints respond

## Key Patterns for Next Feature

- All page components render inside `<Outlet />` within the Shell
- WebSocket URL is computed from `window.location` to support both ws: and wss:
- Navigation checks endpoint availability via HEAD requests on mount
- Health indicator maps API response status: `ok` -> green, `degraded` -> yellow, fetch failure -> red
- Tailwind CSS classes used throughout - no custom CSS needed

## Integration Points

- The `useWebSocket` hook exposes `{ state, send, lastMessage }` - future features can use `lastMessage` for real-time updates
- The Shell layout uses `flex h-screen flex-col` - content area fills remaining space with `overflow-auto`
- Page components receive no props - they can access route params and shared state independently
