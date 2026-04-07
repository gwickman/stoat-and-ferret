# C4 Code Level: GUI Components

## Overview

- **Name**: GUI Components
- **Description**: React/TypeScript presentational component library for video editing interface including timeline, media management, effects, player controls, and system monitoring.
- **Location**: `gui/src/components/` (direct files only; subdirectories `library/`, `render/`, `theater/` documented separately)
- **Language**: TypeScript/React
- **Purpose**: Provides reusable UI components for the stoat-and-ferret video editor frontend, from low-level controls (sliders, buttons) to high-level containers (timeline canvas, effect catalog, player).
- **Parent Component**: [Web GUI](./c4-component-web-gui.md)

## Code Elements

### Timeline Components

- `TimelineCanvas` — Main timeline container with ruler, tracks, zoom (0.1–10x), and horizontal scroll; manages playhead position and clip selection, props: `tracks: Track[]`, `duration: number` (gui/src/components/TimelineCanvas.tsx)
- `Track` — Renders single timeline track with label, mute/lock indicators, and clips within; props: `track: Track`, `zoom: number`, `scrollOffset: number`, `selectedClipId: string | null`, `onSelectClip` (gui/src/components/Track.tsx)
- `TimelineClip` — Position-accurate clip on track with duration display and optional audio waveform; props: `clip: TimelineClip`, `zoom`, `scrollOffset`, `isSelected`, `onSelect`, `trackType?: string` (gui/src/components/TimelineClip.tsx)
- `TimeRuler` — Horizontal time ruler above tracks with zoom-responsive markers; props: `duration`, `zoom`, `scrollOffset`, `canvasWidth`, `pixelsPerSecond?` (gui/src/components/TimeRuler.tsx)
- `Playhead` — Vertical playhead indicator at current playback position; props: `position`, `zoom`, `scrollOffset`, `height` (gui/src/components/Playhead.tsx)
- `AudioWaveform` — Background waveform PNG for audio track clips; props: `videoId: string` (gui/src/components/AudioWaveform.tsx)

### Media Playback Components

- `PreviewPlayer` — HLS.js video player with Safari native fallback (VOD config); tracks buffer and fatal errors; props: `manifestUrl: string | null | undefined`, `onBufferUpdate?: (ranges: BufferRange[]) => void`, `onError?: (msg: string) => void`, `videoRef?: React.RefObject<HTMLVideoElement>` (gui/src/components/PreviewPlayer.tsx)
- `PlayerControls` — Transport controls: play/pause, skip ±5s, progress bar, volume slider with mute, keyboard shortcuts (Space/Arrows); props: `videoRef: React.RefObject<HTMLVideoElement | null>` (gui/src/components/PlayerControls.tsx)
- `ProgressBar` — Clickable progress bar with seek tooltip and thumbnail preview; handles mouse hover for scrubbing; props: `currentTime`, `duration`, `onSeek: (time) => void`, `thumbnailMetadata?: ThumbnailMetadata | null` (gui/src/components/ProgressBar.tsx)
- `VolumeSlider` — Volume slider [0–1] with mute toggle preserving previous volume; props: `volume`, `muted`, `onVolumeChange`, `onMuteToggle` (gui/src/components/VolumeSlider.tsx)
- `SeekTooltip` — Hover tooltip on progress bar showing time and sprite sheet thumbnail preview; props: `hoverTime`, `duration`, `thumbnailMetadata: ThumbnailMetadata | null`, `mouseX`, `barWidth` (gui/src/components/SeekTooltip.tsx)
- `PreviewStatus` — Real-time status display: seek latency (ms), buffer amount, generation progress; props: `videoRef: React.RefObject<HTMLVideoElement>` (gui/src/components/PreviewStatus.tsx)

### Project Management Components

- `ProjectList` — Grid of project cards with load/error/empty states; props: `projects: Project[]`, `clipCounts: Record<string, number>`, `loading`, `error: string | null`, `onSelect`, `onDelete` (gui/src/components/ProjectList.tsx)
- `ProjectCard` — Single project summary: name, creation date, clip count, dimensions, fps; props: `project: Project`, `clipCount: number`, `onSelect`, `onDelete` (gui/src/components/ProjectCard.tsx)
- `ProjectDetails` — Detailed project view with metadata and configuration (gui/src/components/ProjectDetails.tsx)
- `CreateProjectModal` — Modal form to create new project with parameters (gui/src/components/CreateProjectModal.tsx)
- `DeleteConfirmation` — Confirmation modal for project deletion with error handling; props: `open`, `projectId`, `projectName`, `onClose`, `onDeleted` (gui/src/components/DeleteConfirmation.tsx)

### Clip & Track Management Components

- `ClipFormModal` — Add/edit clip modal with video selection, in/out points, timeline position validation; props: `mode: 'add' | 'edit'`, `clip?: Clip`, `projectId`, `onClose`, `onSaved` (gui/src/components/ClipFormModal.tsx)
- `ClipSelector` — Select clips from available sources (gui/src/components/ClipSelector.tsx)
- `LayerStack` — Manage track layers/ordering (gui/src/components/LayerStack.tsx)

### Effects & Filters Components

- `EffectCatalog` — Browsable effect library with search, category filter, grid/list toggle; displays category badges, descriptions, hints; props: none (uses store); (gui/src/components/EffectCatalog.tsx)
- `EffectStack` — Stack of applied effects on selected clip with add/remove/reorder (gui/src/components/EffectStack.tsx)
- `EffectParameterForm` — Form to configure effect parameters (gui/src/components/EffectParameterForm.tsx)
- `FilterPreview` — Real-time filter preview on video (gui/src/components/FilterPreview.tsx)
- `TransitionPanel` — Transition effect selection and configuration (gui/src/components/TransitionPanel.tsx)

### Layout & Composition Components

- `LayoutSelector` — Select layout presets (PiP, side-by-side, grid) from compose store; props: none (uses composeStore); (gui/src/components/LayoutSelector.tsx)
- `LayoutPreview` — Preview of selected layout template (gui/src/components/LayoutPreview.tsx)

### Navigation & Shell Components

- `Shell` — Root layout wrapper with header (Navigation, HealthIndicator), main outlet (React Router), StatusBar footer; props: none (gui/src/components/Shell.tsx)
- `Navigation` — Tab navigation to Dashboard, Library, Projects, Effects, Timeline, Preview, Render; checks endpoint availability on mount; props: none (gui/src/components/Navigation.tsx)
- `StatusBar` — Footer status bar showing WebSocket connection state; props: `connectionState: ConnectionState` (gui/src/components/StatusBar.tsx)

### Library & Media Components

- `VideoGrid` — Responsive grid of video cards with load/error/empty states; props: `videos: Video[]`, `loading`, `error: string | null` (gui/src/components/VideoGrid.tsx)
- `VideoCard` — Video thumbnail, filename, duration, proxy status badge; props: `video: Video` (gui/src/components/VideoCard.tsx)
- `DirectoryBrowser` — File browser for selecting directories to scan (gui/src/components/DirectoryBrowser.tsx)
- `SearchBar` — Search input with debouncing for library filtering (gui/src/components/SearchBar.tsx)
- `ScanModal` — Modal to initiate directory scan for videos (gui/src/components/ScanModal.tsx)
- `SortControls` — Sort options for video/project lists (gui/src/components/SortControls.tsx)
- `QualitySelector` — Select video quality/bitrate for rendering (gui/src/components/QualitySelector.tsx)

### Health & Monitoring Components

- `HealthIndicator` — Status dot and label showing system health (healthy/degraded/unhealthy); props: none (uses useHealth hook); (gui/src/components/HealthIndicator.tsx)
- `HealthCards` — Grid of component status cards (Database, FFmpeg, Preview, Proxy, Render, Rust Core); props: `health: HealthState` (gui/src/components/HealthCards.tsx)
- `MetricsCards` — Performance metrics dashboard (gui/src/components/MetricsCards.tsx)

### Utility & Control Components

- `ZoomControls` — Timeline zoom in/out/reset buttons with limits; props: `zoom`, `onZoomIn`, `onZoomOut`, `onReset`, `minZoom?`, `maxZoom?` (gui/src/components/ZoomControls.tsx)
- `ActivityLog` — Real-time activity event log from WebSocket; parses event messages and displays timestamped entries; props: `lastMessage: MessageEvent | null` (gui/src/components/ActivityLog.tsx)

## Subdirectories

- **library/** — Components for video library management (proxy status badge, library UI elements)
- **render/** — Components for render job tracking (render queue, job cards, progress, status)
- **theater/** — Components for media theater/playback context (large player view, fullscreen modes)

## Dependencies

### Internal Dependencies

- **Stores**: `useTimelineStore`, `useClipStore`, `useEffectCatalogStore`, `useComposeStore`, `usePreviewStore`, `useActivityStore`
- **Hooks**: `useVideos`, `useEffects`, `useHealth`, `useWebSocket`, `useProjects`
- **Utils**: `timelineUtils` (timeToPixel, getMarkerInterval, formatRulerTime), `calculateFrameOffset` (seek tooltip)
- **Generated Types**: `Track`, `Clip`, `Effect`, `Project`, `Video`, `TimelineClip`, `LayoutPreset`
- **Library Components**: `ProxyStatusBadge` (from library/)

### External Dependencies

- **React**: 18.x (hooks: useState, useEffect, useCallback, useRef, useMemo)
- **React Router**: 6.x (NavLink, Outlet, useNavigate)
- **HLS.js**: 1.x (for HLS video streaming with adaptive bitrate)
- **Tailwind CSS**: Styling (responsive design, dark theme)
- **Zustand**: State management (store hooks)

## Relationships

```mermaid
---
title: GUI Component Architecture
---
classDiagram
    namespace Shell_Layout {
        class Shell {
            <<root>>
            +Navigation
            +HealthIndicator
            +Outlet
            +StatusBar
        }
        class Navigation {
            -tabs: TabDef[]
            +checkEndpointAvailability()
        }
        class HealthIndicator {
            -status: HealthStatus
        }
        class StatusBar {
            -connectionState: ConnectionState
        }
    }
    
    namespace Timeline_Editing {
        class TimelineCanvas {
            -zoom: number 0.1-10x
            -scrollOffset: number
            +handleZoomIn/Out/Reset()
            +handleScroll()
        }
        class Track {
            -label: string
            -muted: boolean
            -locked: boolean
        }
        class TimelineClip {
            -timeline_start/end
            -in_point/out_point
            -duration
        }
        class TimeRuler {
            -markers: TimedMarker[]
        }
        class Playhead {
            -position: number
        }
        class AudioWaveform {
            -videoId: string
            -bgUrl: string
        }
    }
    
    namespace Media_Playback {
        class PreviewPlayer {
            -manifestUrl: string
            -usingSafari: boolean
            +initHLS()
            +handleFatalError()
        }
        class PlayerControls {
            -playing: boolean
            +togglePlay()
            +skip()
            +handleKeyboard()
        }
        class ProgressBar {
            -fraction: number
            -hovering: boolean
            +handleClick()
            +handleMouseMove()
        }
        class VolumeSlider {
            -volume: 0-1
            -muted: boolean
            +handleMuteToggle()
        }
        class SeekTooltip {
            -frameIndex: number
            +calculateFrameOffset()
        }
        class PreviewStatus {
            -seekLatency: number
            -bufferRanges: BufferRange[]
        }
    }
    
    namespace Project_Management {
        class ProjectList {
            -projects: Project[]
            -loading/error
        }
        class ProjectCard {
            -clipCount: number
            +formatDate()
        }
        class CreateProjectModal {
            -mode: 'add'
        }
        class DeleteConfirmation {
            -deleting: boolean
        }
    }
    
    namespace Clip_Track_Mgmt {
        class ClipFormModal {
            -mode: 'add'|'edit'
            -validation: string
            +validate()
        }
        class LayerStack {
            -tracks: Track[]
        }
    }
    
    namespace Effects_Filters {
        class EffectCatalog {
            -searchQuery: string
            -selectedCategory: string
            -viewMode: 'grid'|'list'
        }
        class EffectStack {
            -effects: Effect[]
        }
        class FilterPreview {
            -preview: VideoFrame
        }
        class TransitionPanel {
            -transition: Transition
        }
    }
    
    namespace Layout_Composition {
        class LayoutSelector {
            -presets: LayoutPreset[]
            -selectedPreset: string
        }
        class LayoutPreview {
            -layout: LayoutPreset
        }
    }
    
    namespace Library_Media {
        class VideoGrid {
            -videos: Video[]
        }
        class VideoCard {
            -video: Video
            +formatDuration()
        }
        class SearchBar {
            -query: string
        }
        class ScanModal {
            -directory: string
        }
    }
    
    namespace Health_Monitoring {
        class HealthCards {
            -components: Record
        }
        class HealthIndicator {
            -status: HealthStatus
        }
    }

    Shell --> Navigation : renders
    Shell --> HealthIndicator : renders
    Shell --> StatusBar : renders
    
    TimelineCanvas --> Track : maps
    TimelineCanvas --> TimeRuler : above tracks
    TimelineCanvas --> Playhead : overlay
    TimelineCanvas --> ZoomControls : controls
    
    Track --> TimelineClip : contains
    TimelineClip --> AudioWaveform : conditional audio
    
    PreviewPlayer --> PlayerControls : below
    PlayerControls --> ProgressBar : top control
    PlayerControls --> VolumeSlider : bottom control
    
    ProgressBar --> SeekTooltip : on hover
    SeekTooltip -.->|thumbnail_metadata| PreviewStatus
    
    ProjectList --> ProjectCard : maps
    
    EffectCatalog -.->|selectedEffect| EffectStack
    
    LayoutSelector -.->|selectPreset| LayoutPreview
    
    VideoGrid --> VideoCard : maps
    VideoCard -.->|thumbnail| ProxyStatusBadge
```

## Notes

- **Store Integration**: Components heavily use Zustand stores for state management (timeline, clips, effects, compose, preview, activity).
- **Keyboard Accessibility**: PlayerControls and ProgressBar support keyboard navigation (Space, Arrow keys) per WCAG AA.
- **Error Boundaries**: Forms (ClipFormModal, CreateProjectModal) include validation and error state handling.
- **Responsive Design**: Grid components use Tailwind responsive classes (sm:, md:, lg:) for mobile/tablet/desktop.
- **HLS Streaming**: PreviewPlayer uses HLS.js with VOD configuration, automatic Safari native fallback for MPEG-URL support.
- **Performance**: TimelineCanvas uses zoom/scroll offsets to virtualize rendering; ProgressBar uses useCallback for mouse handlers.
- **No Direct API Calls**: Components delegate data fetching to custom hooks (useVideos, useEffects, useHealth) for separation of concerns.
