# C4 Code Level: Preview Player Components

**Source:** `gui/src/components/Preview*.tsx`, `gui/src/components/Player*.tsx`, `gui/src/components/Progress*.tsx`, `gui/src/components/Volume*.tsx`, `gui/src/components/SeekTooltip.tsx`, `gui/src/components/Quality*.tsx`

**Component:** Web GUI

## Purpose

HLS video player with transport controls, progress tracking, quality selection, and seek preview tooltips. Provides a comprehensive playback UI with accessibility features (WCAG AA).

## Code Elements

### PreviewPlayer

**Location:** `gui/src/components/PreviewPlayer.tsx` (line 35)

**Props:**
```typescript
interface PreviewPlayerProps {
  manifestUrl: string | null | undefined
  onBufferUpdate?: (ranges: BufferRange[]) => void
  onError?: (message: string) => void
  videoRef?: React.RefObject<HTMLVideoElement | null>
}
```

**Features:**
- HLS playback via HLS.js (Chrome/Firefox) with Safari native fallback
- Buffer range tracking via `video.buffered` API
- Fatal error recovery with media error recovery and network retry
- VOD configuration: low latency disabled, max buffer 30s, worker enabled
- Graceful degradation when HLS not supported

**Error Handling:**
- `Hls.Events.ERROR` listener catches fatal errors
- Media errors trigger recovery: `hls.recoverMediaError()`
- Network errors trigger reload: `hls.startLoad(-1)`
- Unrecoverable errors destroy instance and call `onError` callback

**Styling:** Full-width rounded video element, black background

**Loading State:** Shows spinner + "Waiting for preview..." when manifestUrl not yet available

### PlayerControls

**Location:** `gui/src/components/PlayerControls.tsx` (line 21)

**Props:**
```typescript
interface PlayerControlsProps {
  videoRef: React.RefObject<HTMLVideoElement | null>
}
```

**Features:**
- Play/pause toggle (syncs with video element pause state)
- Skip forward/backward ±5 seconds
- Progress bar with seek (delegates to ProgressBar)
- Volume control with mute toggle (delegates to VolumeSlider)
- Real-time position and duration sync via timeupdate/durationchange events
- Keyboard accessibility: Space (play/pause), arrows (seek), up/down (volume)

**State Management:**
- `playing` local state (mirrors video.paused)
- Syncs to previewStore: position, duration, volume, muted
- Restores previous volume on unmute via `previousVolumeRef`

**Layout:** Flex column with ProgressBar above button row, rounded border styling

### ProgressBar

**Location:** `gui/src/components/ProgressBar.tsx` (line 32)

**Props:**
```typescript
interface ProgressBarProps {
  currentTime: number
  duration: number
  onSeek: (time: number) => void
  thumbnailMetadata?: ThumbnailMetadata | null
}
```

**Features:**
- Filled bar proportional to currentTime/duration
- Click-to-seek by calculating position from click offset
- Hover tooltip with seek preview (via SeekTooltip)
- Time display: "M:SS" or "H:MM:SS" (uses formatTime utility)
- ARIA attributes for accessibility (progressbar role, aria-valuenow, etc.)

**Interaction:**
- onClick: Calculate seek position from click x-coordinate
- onMouseMove: Update hover time and tooltip position
- onMouseEnter/Leave: Show/hide tooltip

**Helpers:**
- `formatTime(seconds)` - Returns "M:SS" or "H:MM:SS" format with padding

### QualitySelector

**Location:** `gui/src/components/QualitySelector.tsx` (line 17)

**Props:** None (reads from stores)

- **Purpose:** Dropdown for preview quality selection
- **Options:** Low, Medium (default), High
- **Behavior:** Changing quality DELETEs current session and creates new one
- **Disabled:** When status is 'generating' or 'initializing'
- **Callback:** `setQuality(projectId, quality)` from previewStore

**Implementation:** Uses store's setQuality which deletes old session and starts new one at selected quality

### PreviewStatus

**Location:** `gui/src/components/PreviewStatus.tsx` (line 17)

**Props:**
```typescript
interface PreviewStatusProps {
  videoRef: React.RefObject<HTMLVideoElement | null>
}
```

**Features:**
- Real-time seek latency display (measured between seeking/seeked events)
- Buffer indicator: visual bar showing total buffered seconds
- Generation progress: Shows percentage during preview creation
- Updates at ~4Hz via timeupdate/progress events
- Calculates total buffered from all video.buffered ranges

**State:**
- `seekLatency` - Time in ms between seeking and seeked events
- `bufferRanges` - Array of {start, end} time ranges
- Reads from previewStore: status, progress, duration

**Display:**
- Seek latency: "Seek: NNNms" (only shown after seek)
- Buffer bar: Green progress bar showing percentage of total duration
- Generation progress: "Generating: NN%" (only during 'generating' status)

### VolumeSlider

**Location:** `gui/src/components/VolumeSlider.tsx` (line 20)

**Props:**
```typescript
interface VolumeSliderProps {
  volume: number
  muted: boolean
  onVolumeChange: (volume: number) => void
  onMuteToggle: () => void
}
```

**Features:**
- Range input [0, 1] mapped to audio volume
- Mute toggle button (shows muted/unmuted icon)
- Volume restoration on unmute (preserves previous level)
- Syncs to video element: `video.volume = value`

**Styling:** Icon button + range slider, gray hover states

### SeekTooltip

**Location:** `gui/src/components/SeekTooltip.tsx` (line 51)

**Props:**
```typescript
interface SeekTooltipProps {
  hoverTime: number
  duration: number
  thumbnailMetadata: ThumbnailMetadata | null
  mouseX: number
  barWidth: number
}
```

**Features:**
- Time-only display (default, always shown)
- Thumbnail preview from sprite sheet when metadata available
- Positioned above progress bar with clamping to bar edges
- No pointer events (doesn't block clicks)

**Thumbnail Sprite Calculation:**
```typescript
interface ThumbnailMetadata {
  columns: number
  frame_count: number
  frame_height, frame_width: number
  interval_seconds: number
  rows: number
  strip_url: string
}
```

- Frame index: `Math.floor(hoverTime / interval_seconds)`
- Sprite position: `{col, row}` calculated from frame_index, columns, rows
- Background offset: `{bgX: -col*width, bgY: -row*height}`

**Helper:** `calculateFrameOffset(hoverTime, metadata)` returns {frameIndex, bgX, bgY}

## Dependencies

### Internal Dependencies

- **Type imports:** BufferRange (PreviewPlayer), ThumbnailMetadata (SeekTooltip)
- **Stores:** usePreviewStore, useProjectStore (QualitySelector)
- **External ref:** videoRef passed through component hierarchy
- **Utilities:** formatTime (ProgressBar, SeekTooltip)

### External Dependencies

- React: `useState`, `useEffect`, `useCallback`, `useRef`
- HLS.js: For HLS playback (Chrome/Firefox)
- Native Video API: `HTMLVideoElement.prototype.{play, pause, currentTime, volume, muted, buffered}`
- Tailwind CSS for styling

## Key Implementation Details

### HLS.js Configuration (PreviewPlayer)

VOD (video-on-demand) optimized per NFR-002:
```typescript
const HLS_CONFIG: Partial<Hls['config']> = {
  lowLatencyMode: false,      // VOD, not live
  startPosition: -1,          // Auto-start
  maxBufferLength: 30,        // 30 seconds
  enableWorker: true,         // Offload parsing
}
```

### Safari Native HLS Fallback

Browser detection via canPlayType:
```typescript
if (video.canPlayType('application/vnd.apple.mpegurl')) {
  setUsingSafari(true)
  video.src = manifestUrl  // Native HLS support
}
```

### Buffer Tracking (PreviewPlayer, PreviewStatus)

Both components read from `video.buffered` TimeRanges:
```typescript
const getBufferRanges = (): BufferRange[] => {
  const ranges: BufferRange[] = []
  for (let i = 0; i < video.buffered.length; i++) {
    ranges.push({
      start: video.buffered.start(i),
      end: video.buffered.end(i),
    })
  }
  return ranges
}
```

### Seek Latency Measurement (PreviewStatus)

Measures time between `seeking` and `seeked` events:
```typescript
const onSeeking = () => { seekStart = performance.now() }
const onSeeked = () => {
  if (seekStart > 0) {
    setSeekLatency(Math.round(performance.now() - seekStart))
  }
}
```

### Progress Bar Seek Calculation

Click position to time conversion:
```typescript
const rect = e.currentTarget.getBoundingClientRect()
const x = e.clientX - rect.left
const ratio = Math.max(0, Math.min(1, x / rect.width))
onSeek(ratio * duration)
```

### Time Formatting (formatTime)

Conditional hours display:
```typescript
export function formatTime(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  return h > 0 ? `${h}:${pad(m)}:${pad(sec)}` : `${m}:${pad(sec)}`
}
```

Shows "H:MM:SS" for durations >= 1 hour, else "M:SS"

### Mute State Management (PlayerControls)

Volume restoration logic:
```typescript
const handleMuteToggle = () => {
  const newMuted = !muted
  setMuted(newMuted)
  if (newMuted) {
    previousVolumeRef.current = volume > 0 ? volume : previousVolumeRef.current
  } else {
    const restored = previousVolumeRef.current || 1
    setVolume(restored)
  }
}
```

Preserves non-zero volume for restore on unmute.

### Keyboard Accessibility (PlayerControls)

WCAG AA compliant keyboard bindings in PlayerControls:
```typescript
case ' ':       togglePlay()
case 'ArrowLeft':   skip(-5)
case 'ArrowRight':  skip(+5)
case 'ArrowUp':     volume += 0.1
case 'ArrowDown':   volume -= 0.1
```

All handlers prevent default to avoid page scrolling.

## Relationships

```mermaid
---
title: Preview Player Components
---
classDiagram
    namespace Player {
        class PreviewPlayer {
            manifestUrl, videoRef
            HLS.js or Safari native
            onBufferUpdate, onError
        }
        class PlayerControls {
            videoRef, skip, play/pause
            keyboard shortcuts (WCAG AA)
        }
        class VolumeSlider {
            volume, muted state
            previous volume restore
        }
    }

    namespace Progress {
        class ProgressBar {
            currentTime, duration
            click-to-seek
            hover tooltip
        }
        class SeekTooltip {
            hoverTime, thumbnailMetadata
            sprite sheet positioning
        }
    }

    namespace Quality {
        class QualitySelector {
            quality dropdown
            triggers session restart
        }
    }

    namespace Status {
        class PreviewStatus {
            seek latency
            buffer ranges
            generation progress
        }
    }

    namespace Stores {
        class PreviewStore {
            sessionId, status, quality
            position, duration, volume
            connect(), setQuality()
        }
    }

    PreviewPlayer --> PreviewStore
    PlayerControls --> ProgressBar
    PlayerControls --> VolumeSlider
    PlayerControls --> PreviewStore
    ProgressBar --> SeekTooltip
    QualitySelector --> PreviewStore
    PreviewStatus --> PreviewStore
    VolumeSlider -.->|updates video.volume|PreviewPlayer
    PlayerControls -.->|updates video.currentTime|PreviewPlayer
```

## Code Locations

- **PreviewPlayer.tsx**: HLS.js video player with buffer tracking
- **PlayerControls.tsx**: Transport controls with keyboard accessibility
- **ProgressBar.tsx**: Seekable progress bar with optional thumbnail preview
- **VolumeSlider.tsx**: Volume slider with mute toggle
- **SeekTooltip.tsx**: Tooltip for seek preview (time-only or thumbnail sprite)
- **QualitySelector.tsx**: Quality dropdown with session restart
- **PreviewStatus.tsx**: Real-time latency, buffer, and generation progress

## Usage Example

The PreviewPage composes these components together:

```typescript
<TheaterMode videoRef={videoRef}>
  <PreviewPlayer
    manifestUrl={manifestUrl}
    videoRef={videoRef}
    onError={(msg) => setError(msg)}
  />
  {!isFullscreen && (
    <>
      <PlayerControls videoRef={videoRef} />
      <PreviewStatus videoRef={videoRef} />
    </>
  )}
</TheaterMode>
```

PlayerControls syncs with previewStore (position, volume, muted) which flows back to PreviewPlayer via controlled video element.
