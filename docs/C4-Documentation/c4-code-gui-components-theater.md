# C4 Code Level: GUI Theater Mode Components

## Overview

- **Name**: Theater Mode Components
- **Description**: Fullscreen playback interface with auto-hiding HUD overlays showing project info, AI actions, playback controls, and render progress
- **Location**: `gui/src/components/theater`
- **Language**: TypeScript/React
- **Purpose**: Provides immersive fullscreen video preview with contextual controls and real-time render progress/AI action notifications
- **Parent Component**: [Web GUI](./c4-component-web-gui.md)

## Code Elements

### Components

#### TheaterMode
- **Description**: Fullscreen wrapper with auto-hiding HUD overlay. Passes through children when not fullscreen; when active, wraps children with theater container, HUD container, and mouse-tracking behavior that hides HUD after 3 seconds of inactivity.
- **Location**: `gui/src/components/theater/TheaterMode.tsx:23-112`
- **Props Interface**:
  ```typescript
  interface TheaterModeProps {
    children: React.ReactNode  // Content to render (e.g., PreviewPlayer)
    videoRef?: React.RefObject<HTMLVideoElement | null>  // Video element ref for playback controls
  }
  ```
- **State Management** (via theaterStore):
  - `isFullscreen: boolean` — Fullscreen state
  - `isHUDVisible: boolean` — HUD overlay visibility (auto-toggles)
  - `showHUD()` / `hideHUD()` — Actions to control HUD visibility
- **Local State**:
  - `timerRef: ReturnType<typeof setTimeout> | null` — Tracks HUD hide timer
- **Key Behaviors**:
  - Returns children as-is when not fullscreen
  - When fullscreen, wraps children in black theater container with HUD overlay
  - Monitors mouse movement; shows HUD and resets 3-second hide timer
  - Automatically hides HUD after 3 seconds of no mouse movement
  - Handles fullscreen exit/toggle via keyboard shortcuts (via useTheaterShortcuts hook)
  - Cleans up timer on unmount
- **Subcomponents**: Renders TopHUD and BottomHUD (if videoRef provided)
- **Dependencies**: `useTheaterStore`, `useTheaterShortcuts` hook, `useEffect`, `useCallback`, `useRef`

#### TopHUD
- **Description**: Top HUD overlay displaying current project title and AI action indicator with gradient fade background.
- **Location**: `gui/src/components/theater/TopHUD.tsx:12-28`
- **Props**: None
- **Key Behaviors**:
  - Fetches selected project from projectStore and useProjects hook
  - Displays project name (defaults to "Untitled Project" if not found)
  - Renders AIActionIndicator component for live AI action display
  - Uses gradient background (black at top, transparent at bottom) for readability
  - Positioned absolutely at top with pointer-events-auto for interactivity
- **Dependencies**: `useProjectStore`, `useProjects` hook, `AIActionIndicator` component

#### BottomHUD
- **Description**: Bottom HUD overlay with full playback controls and optional render progress bar with percentage and ETA, updated via RENDER_PROGRESS WebSocket events.
- **Location**: `gui/src/components/theater/BottomHUD.tsx:42-83`
- **Props Interface**:
  ```typescript
  interface BottomHUDProps {
    videoRef: React.RefObject<HTMLVideoElement | null>  // Ref to video element for playback control
  }
  ```
- **State Management**:
  - `renderProgress: RenderProgressState | null` — Current render progress (progress: 0-1, etaSeconds: number | null)
  - Listens to WebSocket RENDER_PROGRESS events
- **Key Behaviors**:
  - Renders PlayerControls component with videoRef for play/pause/seeking
  - If render progress available, shows progress bar with green fill and percentage + ETA
  - Progress bar width clamped to 0-100%
  - ETA formatted using formatEta utility (e.g., 150 → "2m 30s")
  - Only renders progress section if renderProgress state is not null
  - Uses gradient background (black at bottom, transparent at top) for readability
  - Positioned absolutely at bottom with pointer-events-auto
- **WebSocket Format** (RENDER_PROGRESS):
  ```typescript
  interface RenderProgressEvent {
    type: 'render_progress'
    payload: {
      progress: number        // 0-1 value
      eta_seconds: number | null
    }
  }
  ```
- **Dependencies**: `useWebSocket` hook, `PlayerControls` component, `useEffect`, `useState`

#### AIActionIndicator
- **Description**: Displays latest AI action description from WebSocket AI_ACTION events. Returns null when disconnected or no action text available (graceful degradation).
- **Location**: `gui/src/components/theater/AIActionIndicator.tsx:22-50`
- **Props**: None
- **State Management**:
  - `actionText: string | null` — Latest AI action description
  - WebSocket connection state from useWebSocket hook
- **Key Behaviors**:
  - Listens to WebSocket AI_ACTION event type
  - Updates actionText when event.payload.description arrives
  - Returns null if disconnected or no actionText (no visual indicator)
  - Displays text with truncation and blue color
  - Gracefully ignores non-JSON messages
- **WebSocket Format** (AI_ACTION):
  ```typescript
  interface AIActionEvent {
    type: 'ai_action'
    payload: {
      description: string
    }
  }
  ```
- **Dependencies**: `useWebSocket` hook, `useEffect`, `useState`

### Utility Functions

#### formatEta (BottomHUD)
- **Signature**: `formatEta(seconds: number): string`
- **Location**: `gui/src/components/theater/BottomHUD.tsx:23-28`
- **Description**: Converts ETA seconds to human-readable format (e.g., 150 → "2m 30s")
- **Returns**: Formatted string with minutes and seconds

#### wsUrl (BottomHUD & AIActionIndicator)
- **Signature**: `wsUrl(): string`
- **Location**: Both files
- **Description**: Constructs WebSocket URL by detecting protocol (wss for HTTPS, ws for HTTP) and using current window location
- **Returns**: WebSocket URL string

### Types/Interfaces

#### TheaterModeProps
- **Location**: `gui/src/components/theater/TheaterMode.tsx:9-14`
- **Fields**: `children: React.ReactNode`, `videoRef?: React.RefObject<HTMLVideoElement | null>`

#### BottomHUDProps
- **Location**: `gui/src/components/theater/BottomHUD.tsx:30-33`
- **Fields**: `videoRef: React.RefObject<HTMLVideoElement | null>`

#### RenderProgressState
- **Location**: `gui/src/components/theater/BottomHUD.tsx:13-16`
- **Fields**: `progress: number`, `etaSeconds: number | null`

#### RenderProgressEvent
- **Location**: `gui/src/components/theater/BottomHUD.tsx:5-11`
- **Fields**: `type: string`, `payload: { progress: number; eta_seconds: number | null }`

#### AIActionEvent
- **Location**: `gui/src/components/theater/AIActionIndicator.tsx:4-9`
- **Fields**: `type: string`, `payload: { description: string }`

### Constants

#### HUD_HIDE_DELAY_MS
- **Location**: `gui/src/components/theater/TheaterMode.tsx:7`
- **Value**: `3000` (milliseconds)
- **Description**: Delay before HUD auto-hides after last mouse movement

## Dependencies

### Internal Dependencies
- `TopHUD` component — Displays project title and AI action
- `BottomHUD` component — Displays playback controls and render progress
- `AIActionIndicator` component — Shows live AI action text
- `PlayerControls` component — External playback control component
- `useTheaterStore` hook — Manages fullscreen and HUD visibility state
- `useTheaterShortcuts` hook — Handles keyboard shortcuts in fullscreen
- `useWebSocket` hook — Manages WebSocket connections for real-time events
- `useProjects` hook — Fetches project list
- `useProjectStore` hook — Provides selected project ID

### External Dependencies
- React 18+ (`useEffect`, `useCallback`, `useRef`, `useState`)
- Tailwind CSS (for styling)
- WebSocket API (browser-native)
- Fullscreen API (browser-native)

## Relationships

```mermaid
---
title: Code Diagram for Theater Mode Components
---
classDiagram
    namespace TheaterMode {
        class TheaterMode {
            -isFullscreen: boolean
            -isHUDVisible: boolean
            -timerRef: RefObject~Timeout~
            +handleMouseMove(): void
            +toggleFullscreen(): Promise~void~
            +exitFullscreen(): Promise~void~
            +render(): JSX.Element
        }
        class TopHUD {
            -selectedProjectId: string | null
            +render(): JSX.Element
        }
        class BottomHUD {
            -renderProgress: RenderProgressState | null
            +formatEta(seconds): string
            +render(videoRef): JSX.Element
        }
        class AIActionIndicator {
            -actionText: string | null
            +render(): JSX.Element | null
        }
    }

    class TheaterStore {
        <<external>>
        +isFullscreen: boolean
        +isHUDVisible: boolean
        +showHUD(): void
        +hideHUD(): void
    }

    class ProjectStore {
        <<external>>
        +selectedProjectId: string | null
    }

    class WebSocketHook {
        <<external>>
        +useWebSocket(url): {lastMessage, state}
    }

    class PlayerControls {
        <<external>>
    }

    TheaterMode --> TheaterStore : reads/writes state
    TheaterMode --> TopHUD : renders
    TheaterMode --> BottomHUD : renders conditionally
    TopHUD --> ProjectStore : reads selectedProjectId
    TopHUD --> AIActionIndicator : renders
    BottomHUD --> WebSocketHook : subscribes to render_progress
    AIActionIndicator --> WebSocketHook : subscribes to ai_action
    BottomHUD --> PlayerControls : renders with videoRef
```

## Notes

- TheaterMode is a container component that orchestrates fullscreen state and HUD visibility
- HUD auto-hide timer is cleared/restarted on every mouse movement, resetting the 3-second countdown
- Both BottomHUD and AIActionIndicator gracefully handle missing WebSocket messages (return null or ignore)
- TopHUD uses `useProjects()` hook which may fetch from server; project lookup has fallback
- Theater mode allows keyboard shortcuts (exit fullscreen, toggle) via useTheaterShortcuts hook
- Pointer events are disabled on HUD wrapper but enabled on individual HUD components for interaction
- VideoRef is optional in TheaterMode props; BottomHUD only renders if videoRef is provided
