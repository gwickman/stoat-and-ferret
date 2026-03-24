# Phase 4: GUI Integration

## Overview

Phase 4 adds two major GUI features: an embedded preview player with HLS.js integration, and AI Theater Mode for full-screen spectator viewing. Both build on the existing React + Vite + Tailwind stack and WebSocket infrastructure.

## Preview Player Component

### Layout

```
┌─────────────────────────────────────────────────────────┐
│  Preview                              [Theater Mode]    │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────┐   │
│  │                                                  │   │
│  │              VIDEO PREVIEW CANVAS                │   │
│  │                                                  │   │
│  │         (HLS.js player with poster frame)        │   │
│  │                                                  │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Thumbnail strip (seek preview on hover)          │   │
│  └──────────────────────────────────────────────────┘   │
│  ═══════════════════●═══════════════════ 12:34 / 45:30  │
│  [|<] [<<] [>/||] [>>] [>|]  Vol ████████░░  [720p v]  │
│  Status: Ready | Latency: 45ms | Buffered: 20.0s       │
└─────────────────────────────────────────────────────────┘
```

### HLS.js Integration

```typescript
// src/components/preview/PreviewPlayer.tsx

import Hls from 'hls.js';
import { useRef, useEffect } from 'react';
import { usePreviewStore } from '../../stores/previewStore';

interface PreviewPlayerProps {
  sessionId: string;
  manifestUrl: string;
  onTimeUpdate: (time: number) => void;
  onError: (error: string) => void;
}

function PreviewPlayer({ sessionId, manifestUrl, onTimeUpdate, onError }: PreviewPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);
  const { setBufferedTo, setLatency } = usePreviewStore();

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    if (Hls.isSupported()) {
      const hls = new Hls({
        maxBufferLength: 30,
        maxMaxBufferLength: 60,
        startLevel: -1,  // auto quality selection
      });
      hls.loadSource(manifestUrl);
      hls.attachMedia(video);

      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) {
          onError(data.details);
        }
      });

      hlsRef.current = hls;
      return () => hls.destroy();
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      // Safari native HLS
      video.src = manifestUrl;
    }
  }, [manifestUrl]);

  return (
    <video
      ref={videoRef}
      data-testid="preview-video"
      onTimeUpdate={() => {
        const video = videoRef.current;
        if (video) {
          onTimeUpdate(video.currentTime);
          if (video.buffered.length > 0) {
            setBufferedTo(video.buffered.end(video.buffered.length - 1));
          }
        }
      }}
    />
  );
}
```

### Player Controls

```typescript
// src/components/preview/PlayerControls.tsx

interface PlayerControlsProps {
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  muted: boolean;
  quality: string;
  onPlay: () => void;
  onPause: () => void;
  onSeek: (time: number) => void;
  onVolumeChange: (volume: number) => void;
  onMuteToggle: () => void;
  onQualityChange: (quality: string) => void;
}
```

Controls include:
- Skip to start / skip back 5s / play-pause / skip forward 5s / skip to end
- Volume slider with mute toggle
- Quality dropdown (540p / 720p / 1080p)
- Full progress bar with seek-on-click and thumbnail preview on hover

### Seek Preview Tooltip

When hovering over the progress bar, a thumbnail from the strip is shown:

```typescript
// src/components/preview/SeekTooltip.tsx

interface SeekTooltipProps {
  stripUrl: string;        // thumbnail strip image URL
  frameWidth: number;       // width of each frame in strip
  frameCount: number;       // total frames in strip
  intervalSeconds: number;  // time between frames
  hoverPosition: number;    // 0.0-1.0 across progress bar
  duration: number;         // total video duration
}
```

The tooltip calculates which frame to show based on hover position and uses CSS `background-position` to display the correct frame from the sprite sheet.

### Timeline Synchronization

The preview player synchronizes with the timeline canvas:

```typescript
// src/hooks/useTimelineSync.ts

function useTimelineSync(videoRef: RefObject<HTMLVideoElement>) {
  const { playheadPosition, setPlayheadPosition } = useTimelineStore();
  const { currentTime } = usePreviewStore();

  // Player → Timeline: update playhead as video plays
  useEffect(() => {
    setPlayheadPosition(currentTime);
  }, [currentTime]);

  // Timeline → Player: seek when user clicks on timeline
  useEffect(() => {
    if (videoRef.current && Math.abs(videoRef.current.currentTime - playheadPosition) > 0.5) {
      videoRef.current.currentTime = playheadPosition;
    }
  }, [playheadPosition]);
}
```

## AI Theater Mode

### Purpose

Transform the user into a spectator watching AI edit their video project. Full-screen video canvas with minimal overlay showing AI actions and progress.

### Visual Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Running Montage                 Adding text overlay "Ch 1"  │  <- Top HUD
│                                                              │
│                                                              │
│                                                              │
│                                                              │
│                      VIDEO CANVAS                            │
│                   (full viewport)                             │
│                                                              │
│                                                              │
│                                                              │
│                                                              │
│  ══════════════════●══════════════════════  12:34 / 45:30    │  <- Bottom HUD
│  [|<]  [>/||]  [>|]   Vol ████░░   [Exit Theater]           │
└──────────────────────────────────────────────────────────────┘
```

### Auto-Hiding HUD

The HUD (heads-up display) auto-hides after 3 seconds of mouse inactivity:

```typescript
// src/components/theater/TheaterHUD.tsx

function TheaterHUD({ children }: { children: React.ReactNode }) {
  const [visible, setVisible] = useState(true);
  const timerRef = useRef<number>();

  const showHUD = useCallback(() => {
    setVisible(true);
    clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => setVisible(false), 3000);
  }, []);

  useEffect(() => {
    document.addEventListener('mousemove', showHUD);
    document.addEventListener('keydown', showHUD);
    return () => {
      document.removeEventListener('mousemove', showHUD);
      document.removeEventListener('keydown', showHUD);
      clearTimeout(timerRef.current);
    };
  }, [showHUD]);

  return (
    <div
      data-testid="theater-hud"
      className={`transition-opacity duration-300 ${visible ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
    >
      {children}
    </div>
  );
}
```

### AI Action Display

Shows real-time AI actions via WebSocket events:

```typescript
// src/components/theater/AIActionIndicator.tsx

interface AIActionIndicatorProps {
  action: AIActionEvent | null;
}

function AIActionIndicator({ action }: AIActionIndicatorProps) {
  if (!action) return null;

  return (
    <div data-testid="ai-action-indicator" className="text-white/80 text-sm">
      <span className="animate-pulse mr-2">AI</span>
      {action.description}
    </div>
  );
}
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Space | Play / Pause |
| Escape | Exit Theater Mode |
| F | Toggle fullscreen |
| M | Mute / unmute |
| Left Arrow | Seek back 5 seconds |
| Right Arrow | Seek forward 5 seconds |
| Up Arrow | Volume up 10% |
| Down Arrow | Volume down 10% |
| Home | Jump to start |
| End | Jump to end |

```typescript
// src/hooks/useTheaterShortcuts.ts

function useTheaterShortcuts(controls: PlayerControlActions) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      switch (e.key) {
        case ' ':         e.preventDefault(); controls.togglePlay(); break;
        case 'Escape':    controls.exitTheater(); break;
        case 'f':         controls.toggleFullscreen(); break;
        case 'm':         controls.toggleMute(); break;
        case 'ArrowLeft': controls.seekRelative(-5); break;
        case 'ArrowRight':controls.seekRelative(5); break;
        case 'ArrowUp':   e.preventDefault(); controls.adjustVolume(0.1); break;
        case 'ArrowDown': e.preventDefault(); controls.adjustVolume(-0.1); break;
        case 'Home':      controls.seekTo(0); break;
        case 'End':       controls.seekTo(controls.duration); break;
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [controls]);
}
```

### Theater Mode Entry/Exit

```typescript
// src/components/theater/TheaterMode.tsx

function TheaterMode() {
  const { isTheaterMode, exitTheaterMode } = usePreviewStore();
  const containerRef = useRef<HTMLDivElement>(null);

  // Enter browser fullscreen when theater mode is activated
  useEffect(() => {
    if (isTheaterMode && containerRef.current) {
      containerRef.current.requestFullscreen?.();
    }
    return () => {
      if (document.fullscreenElement) {
        document.exitFullscreen?.();
      }
    };
  }, [isTheaterMode]);

  // Exit theater mode if user exits fullscreen via browser
  useEffect(() => {
    const handler = () => {
      if (!document.fullscreenElement && isTheaterMode) {
        exitTheaterMode();
      }
    };
    document.addEventListener('fullscreenchange', handler);
    return () => document.removeEventListener('fullscreenchange', handler);
  }, [isTheaterMode, exitTheaterMode]);

  if (!isTheaterMode) return null;

  return (
    <div ref={containerRef} data-testid="theater-mode" className="fixed inset-0 z-50 bg-black">
      <PreviewPlayer /* ... */ />
      <TheaterHUD>
        <TopHUD />
        <BottomHUD />
      </TheaterHUD>
    </div>
  );
}
```

## State Management

### Preview Store (Zustand)

```typescript
// src/stores/previewStore.ts

interface PreviewState {
  // Session
  sessionId: string | null;
  sessionStatus: 'idle' | 'initializing' | 'generating' | 'ready' | 'error';
  manifestUrl: string | null;

  // Playback
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  muted: boolean;
  quality: '540p' | '720p' | '1080p';
  bufferedTo: number;
  latency: number;

  // Theater mode
  isTheaterMode: boolean;
  hudVisible: boolean;
  aiAction: AIActionEvent | null;
  renderProgress: RenderProgressEvent | null;

  // Actions
  startPreview: (projectId: string, quality?: string) => Promise<void>;
  stopPreview: () => Promise<void>;
  seekTo: (position: number) => Promise<void>;
  setPlaying: (playing: boolean) => void;
  setVolume: (volume: number) => void;
  setMuted: (muted: boolean) => void;
  setQuality: (quality: string) => void;
  enterTheaterMode: () => void;
  exitTheaterMode: () => void;
  setBufferedTo: (time: number) => void;
  setLatency: (ms: number) => void;
}
```

### WebSocket Event Handling

Extend the existing `useWebSocket` hook to handle Phase 4 events:

```typescript
// src/hooks/useWebSocket.ts (additions)

// Inside the message handler switch:
case 'preview.ready':
  usePreviewStore.getState().onPreviewReady(event);
  break;
case 'preview.generating':
  usePreviewStore.getState().onPreviewProgress(event);
  break;
case 'preview.error':
  usePreviewStore.getState().onPreviewError(event);
  break;
case 'ai_action':
  usePreviewStore.getState().aiAction = event;
  break;
case 'render_progress':
  usePreviewStore.getState().renderProgress = event;
  break;
case 'proxy.ready':
  // Refresh video list to show proxy status
  useVideoStore.getState().refreshVideos();
  break;
```

## Component File Structure

```
gui/src/
├── components/
│   ├── preview/
│   │   ├── PreviewPlayer.tsx          # HLS.js video element wrapper
│   │   ├── PlayerControls.tsx         # Transport controls bar
│   │   ├── ProgressBar.tsx            # Seekable progress bar
│   │   ├── SeekTooltip.tsx            # Thumbnail preview on hover
│   │   ├── VolumeSlider.tsx           # Volume control with mute
│   │   ├── QualitySelector.tsx        # 540p/720p/1080p dropdown
│   │   └── PreviewStatus.tsx          # Status/latency/buffer display
│   │
│   └── theater/
│       ├── TheaterMode.tsx            # Full-screen wrapper + entry/exit
│       ├── TheaterHUD.tsx             # Auto-hiding overlay container
│       ├── TopHUD.tsx                 # Project title + AI action
│       ├── BottomHUD.tsx              # Controls + progress
│       ├── AIActionIndicator.tsx      # Real-time AI status text
│       └── TheaterProgressBar.tsx     # Full-width thin progress bar
│
├── stores/
│   └── previewStore.ts                # Preview + theater state
│
├── hooks/
│   ├── useTimelineSync.ts             # Player <-> timeline sync
│   ├── useTheaterShortcuts.ts         # Keyboard shortcut handler
│   └── usePreviewSession.ts           # Preview API integration
│
├── api/
│   └── preview.ts                     # Preview/proxy REST API client
│
└── types/
    └── preview.ts                     # PreviewSession, PlaybackState, etc.
```

## Audio Waveform in Timeline

The timeline canvas gains audio waveform visualization for audio tracks:

```typescript
// src/components/timeline/AudioWaveform.tsx

interface AudioWaveformProps {
  videoId: number;
  trackWidth: number;     // pixels
  trackHeight: number;    // pixels
  startTime: number;      // clip start on timeline
  duration: number;       // clip duration
}
```

Waveform is displayed as a background in audio track clips, fetched from the waveform API endpoint.

## Proxy Status Indicators

The library browser gains proxy status indicators on video cards:

```
┌────────────────┐
│  [thumbnail]   │
│                │
│  filename.mp4  │
│  1080p | 2:30  │
│  Proxy: Ready  │  <- green dot for ready, yellow for generating
└────────────────┘
```

## Navigation Updates

Add Preview tab/button to the navigation bar, alongside existing tabs:

```
[Dashboard] [Library] [Projects] [Effects] [Timeline] [Preview]
```

Preview page shows the preview player with controls, or a prompt to select a project and start preview.
