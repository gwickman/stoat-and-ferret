# C4 Code Level: GUI Library Components

## Overview

- **Name**: Library Components
- **Description**: UI component for displaying proxy generation status with real-time WebSocket updates
- **Location**: `gui/src/components/library`
- **Language**: TypeScript/React
- **Purpose**: Provides visual indicator for video proxy status (ready, generating, or none) with live WebSocket subscription
- **Parent Component**: [Web GUI](./c4-component-web-gui.md)

## Code Elements

### Components

#### ProxyStatusBadge
- **Description**: Displays a colored dot indicator showing the current proxy generation status for a video asset. Subscribes to WebSocket PROXY_READY events for real-time updates. Color: green=ready, yellow=generating, gray=none.
- **Location**: `gui/src/components/library/ProxyStatusBadge.tsx:34-65`
- **Props Interface**:
  ```typescript
  interface ProxyStatusBadgeProps {
    videoId: string           // Unique identifier of the video
    proxyStatus?: ProxyStatusValue  // Initial proxy status ('ready' | 'generating' | 'none'), defaults to 'none'
  }
  ```
- **State Management**:
  - `status: ProxyStatusValue` — Current proxy status
  - Uses `useWebSocket()` to subscribe to real-time updates
  - Updates on `proxyStatus` prop changes
  - Listens for WebSocket messages with type='proxy.ready' and matching video_id
- **Key Behaviors**:
  - Renders a small circular dot (h-2.5 w-2.5) with Tailwind color classes
  - On mount, syncs initial status from props
  - Parses WebSocket events and updates status when PROXY_READY event matches videoId
  - Displays tooltip with status label on hover
- **Dependencies**: `useWebSocket()` hook, `useEffect`, `useState`

### Types/Interfaces

#### ProxyStatusValue
- **Type**: `type ProxyStatusValue = 'ready' | 'generating' | 'none'`
- **Location**: `gui/src/components/library/ProxyStatusBadge.tsx:4`
- **Description**: Enumeration of possible proxy generation states

### Constants

#### STATUS_COLORS
- **Location**: `gui/src/components/library/ProxyStatusBadge.tsx:11-15`
- **Description**: Maps ProxyStatusValue to Tailwind background color classes
  ```typescript
  'ready': 'bg-green-500'
  'generating': 'bg-yellow-500'
  'none': 'bg-gray-500'
  ```

#### STATUS_LABELS
- **Location**: `gui/src/components/library/ProxyStatusBadge.tsx:17-21`
- **Description**: Maps ProxyStatusValue to human-readable status labels for tooltips
  ```typescript
  'ready': 'Proxy ready'
  'generating': 'Proxy generating'
  'none': 'No proxy'
  ```

### Utility Functions

#### wsUrl
- **Signature**: `wsUrl(): string`
- **Location**: `gui/src/components/library/ProxyStatusBadge.tsx:23-26`
- **Description**: Constructs the WebSocket URL by detecting protocol (wss for HTTPS, ws for HTTP) and using current window location
- **Returns**: WebSocket URL string (e.g., `ws://localhost:8000/ws`)

## Dependencies

### Internal Dependencies
- `useWebSocket` hook from `../../hooks/useWebSocket` — Manages WebSocket connection and message parsing
- `useState` from React — For status state management
- `useEffect` from React — For lifecycle management and sync

### External Dependencies
- React 18+ (`useEffect`, `useState`)
- Tailwind CSS (for styling)
- WebSocket API (browser-native)

## Relationships

```mermaid
---
title: Code Diagram for Library Components
---
classDiagram
    namespace Library {
        class ProxyStatusBadge {
            -status: ProxyStatusValue
            +render(): JSX.Element
            -wsUrl(): string
        }
        class ProxyStatusValue {
            <<type>>
        }
        class WebSocketHook {
            <<external>>
            +useWebSocket(url): {lastMessage, state}
        }
    }

    class RenderStore {
        <<external>>
    }

    ProxyStatusBadge --> ProxyStatusValue : uses type
    ProxyStatusBadge --> WebSocketHook : subscribes to
    ProxyStatusBadge --|> React : inherits from
```

## Notes

- Component gracefully ignores malformed JSON messages from WebSocket
- Status updates are driven by both props (initial sync) and WebSocket events (reactive)
- Used primarily in library/asset browsers to show proxy generation progress
- No external API calls; all data comes from WebSocket subscription
