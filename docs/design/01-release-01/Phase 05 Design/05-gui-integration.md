# Phase 5: GUI Integration

## Overview

Phase 5 adds two major GUI features: a Render Control Center for job management and progress monitoring, and a Render Settings panel for output configuration. Both build on the existing React + Vite + Tailwind stack and WebSocket infrastructure. The render progress display integrates with the AI Theater Mode established in Phase 4.

## Render Control Center

### Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Render                                          [Start Render]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Queue Status: 2 active / 3 pending / 2 max concurrent           │
│  Disk Free: 47.2 GB  |  HW Accel: NVENC available               │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  Active Renders                                            │   │
│  │  ─────────────────────────────────────────────────────────│   │
│  │  ┌─────────────────────────────────────────────────────┐  │   │
│  │  │ ● Running Montage → my_video.mp4                    │  │   │
│  │  │   MP4 H.264 (NVENC) | High | 1920x1080 30fps       │  │   │
│  │  │   ████████████████████░░░░░░░░░  67%  ETA: 0:22     │  │   │
│  │  │   Frame 6030/9000 | 145 fps | 4.8x realtime        │  │   │
│  │  │                                          [Cancel]    │  │   │
│  │  └─────────────────────────────────────────────────────┘  │   │
│  │  ┌─────────────────────────────────────────────────────┐  │   │
│  │  │ ● Birthday Montage → birthday.mp4                   │  │   │
│  │  │   MP4 H.264 (libx264) | Medium | 1280x720 30fps    │  │   │
│  │  │   ████████░░░░░░░░░░░░░░░░░░░░  28%  ETA: 1:45     │  │   │
│  │  │   Frame 2520/9000 | 42 fps | 1.4x realtime         │  │   │
│  │  │                                          [Cancel]    │  │   │
│  │  └─────────────────────────────────────────────────────┘  │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  Pending (3)                                               │   │
│  │  ─────────────────────────────────────────────────────────│   │
│  │  1. Vacation Highlights → vacation.mp4  (MP4, High)       │   │
│  │  2. Concert Clips → concert.webm  (WebM, Medium)         │   │
│  │  3. Trip 2024 → trip.mov  (ProRes, High)                  │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  Recent History                                 [Clear All]│   │
│  │  ─────────────────────────────────────────────────────────│   │
│  │  ✓ Demo Reel → demo.mp4  | 375 MB | 1:02 | 4.8x | NVENC │   │
│  │  ✗ Slideshow → slides.mp4  | Failed: encoder error        │   │
│  │     [Retry] [Delete]                                       │   │
│  │  ✓ Interview → interview.mp4  | 1.2 GB | 5:30 | 1.1x     │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Render Job Card Component

```typescript
// src/components/render/RenderJobCard.tsx

interface RenderJobCardProps {
  job: RenderJob;
  onCancel: (jobId: string) => void;
  onRetry: (jobId: string) => void;
  onDelete: (jobId: string) => void;
}

function RenderJobCard({ job, onCancel, onRetry, onDelete }: RenderJobCardProps) {
  const isActive = job.status === 'rendering' || job.status === 'pass_1' || job.status === 'pass_2';
  const isFailed = job.status === 'failed';
  const isCompleted = job.status === 'completed';

  return (
    <div data-testid={`render-job-${job.job_id}`} className="border rounded p-3 mb-2">
      <div className="flex justify-between items-start">
        <div>
          <span className="font-medium">{job.project_name}</span>
          <span className="text-gray-500 mx-2">→</span>
          <span className="text-sm">{job.output_path}</span>
        </div>
        <StatusBadge status={job.status} />
      </div>

      <div className="text-xs text-gray-500 mt-1">
        {job.output_format.toUpperCase()} {job.encoder}
        {job.hardware_accelerated && ' (HW)'}
        {' | '}{job.quality_preset}
        {' | '}{job.output_width}x{job.output_height} {job.output_fps}fps
      </div>

      {isActive && (
        <>
          <ProgressBar
            progress={job.progress}
            eta={job.eta_seconds}
            data-testid={`render-progress-${job.job_id}`}
          />
          <div className="text-xs text-gray-500 mt-1">
            Frame {job.current_frame}/{job.total_frames}
            {' | '}{job.fps.toFixed(0)} fps
            {' | '}{renderSpeedLabel(job)}
          </div>
          <button
            data-testid={`render-cancel-${job.job_id}`}
            onClick={() => onCancel(job.job_id)}
            className="text-sm text-red-500 mt-1"
          >
            Cancel
          </button>
        </>
      )}

      {isFailed && (
        <div className="mt-1">
          <span className="text-sm text-red-500">{job.error_message}</span>
          <div className="mt-1 space-x-2">
            <button data-testid={`render-retry-${job.job_id}`} onClick={() => onRetry(job.job_id)}>
              Retry
            </button>
            <button data-testid={`render-delete-${job.job_id}`} onClick={() => onDelete(job.job_id)}>
              Delete
            </button>
          </div>
        </div>
      )}

      {isCompleted && (
        <div className="text-xs text-gray-500 mt-1">
          {formatBytes(job.file_size_bytes)} | {formatDuration(job.elapsed_seconds)}
          {' | '}{renderSpeedLabel(job)}
          {job.hardware_accelerated && ` | ${job.encoder}`}
        </div>
      )}
    </div>
  );
}
```

### Progress Bar Component

```typescript
// src/components/render/RenderProgressBar.tsx

interface RenderProgressBarProps {
  progress: number;    // 0.0 to 1.0
  eta: number | null;  // seconds remaining
  twoPass?: boolean;
  passNumber?: number;
}

function RenderProgressBar({ progress, eta, twoPass, passNumber }: RenderProgressBarProps) {
  return (
    <div data-testid="render-progress-bar" className="mt-2">
      <div className="flex justify-between text-xs mb-1">
        <span>
          {twoPass && passNumber ? `Pass ${passNumber}: ` : ''}
          {(progress * 100).toFixed(0)}%
        </span>
        <span>ETA: {eta != null ? formatETA(eta) : '—'}</span>
      </div>
      <div className="w-full bg-gray-200 rounded h-2">
        <div
          className="bg-blue-500 rounded h-2 transition-all duration-300"
          style={{ width: `${Math.min(progress * 100, 100)}%` }}
        />
      </div>
    </div>
  );
}
```

## Start Render Modal

### Layout

```
┌──────────────────────────────────────────────────────────┐
│  Start Render                                      [X]    │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  Project: [Running Montage          v]                     │
│                                                            │
│  ─── Output Settings ───────────────────────────────────  │
│                                                            │
│  Format:    [MP4 (H.264)    v]                             │
│  Quality:   [● Draft ○ Medium ○ High ○ Lossless]          │
│  Resolution: [1920] x [1080]  FPS: [30.0]                 │
│  Two-pass:   [  ] Enable (slower, better quality)          │
│                                                            │
│  ─── Encoder ───────────────────────────────────────────  │
│                                                            │
│  Hardware:  ● h264_nvenc (NVIDIA GPU)                      │
│             ○ libx264 (Software)                           │
│  Status:    ✓ NVENC available                              │
│                                                            │
│  ─── Output ────────────────────────────────────────────  │
│                                                            │
│  Path: [/home/user/output/running_montage.mp4] [Browse]    │
│                                                            │
│  Estimated size: ~375 MB                                   │
│  Disk free: 47.2 GB  ✓                                     │
│                                                            │
│  ─── FFmpeg Command Preview ────────────────────────────  │
│  │ ffmpeg -y -i input1.mp4 -i input2.mp4                │  │
│  │   -filter_complex "..." -c:v h264_nvenc -crf 18      │  │
│  │   -preset slow -c:a aac -b:a 192k output.mp4        │  │
│                                                            │
│                          [Cancel]  [Start Render]          │
└──────────────────────────────────────────────────────────┘
```

### Render Settings Component

```typescript
// src/components/render/RenderSettingsForm.tsx

interface RenderSettingsFormProps {
  projectId: string;
  formats: OutputFormatInfo[];
  encoders: EncoderInfo[];
  onSubmit: (settings: RenderSettings) => void;
  onCancel: () => void;
}

function RenderSettingsForm({
  projectId, formats, encoders, onSubmit, onCancel
}: RenderSettingsFormProps) {
  const [format, setFormat] = useState<string>('mp4');
  const [quality, setQuality] = useState<string>('high');
  const [width, setWidth] = useState(1920);
  const [height, setHeight] = useState(1080);
  const [fps, setFps] = useState(30.0);
  const [twoPass, setTwoPass] = useState(true);  // default on for "high" quality
  const [outputPath, setOutputPath] = useState('');
  const [encoder, setEncoder] = useState<string>('');

  const { diskFree, estimatedSize } = useRenderEstimate(format, quality, width, height, fps);
  const { commandPreview } = useCommandPreview(projectId, format, quality, encoder, width, height, fps, twoPass);

  // Auto-select best encoder when format changes
  useEffect(() => {
    const bestEncoder = encoders
      .filter(e => e.supported_formats.includes(format) && e.available)
      .sort((a, b) => a.priority - b.priority)[0];
    if (bestEncoder) setEncoder(bestEncoder.name);
  }, [format, encoders]);

  // Auto-generate output path from project name
  useEffect(() => {
    const ext = formats.find(f => f.id === format)?.extension || '.mp4';
    setOutputPath(`${defaultOutputDir}/${projectName}${ext}`);
  }, [format, projectName]);

  return (
    <form data-testid="render-settings-form" onSubmit={handleSubmit}>
      {/* ... form fields as shown in layout ... */}
    </form>
  );
}
```

### FFmpeg Command Preview

```typescript
// src/components/render/CommandPreview.tsx

interface CommandPreviewProps {
  command: string | null;
}

function CommandPreview({ command }: CommandPreviewProps) {
  if (!command) return null;

  return (
    <div data-testid="command-preview" className="mt-2">
      <details>
        <summary className="text-sm text-gray-500 cursor-pointer">
          FFmpeg Command Preview
        </summary>
        <pre className="text-xs bg-gray-100 p-2 rounded mt-1 overflow-x-auto">
          {command}
        </pre>
      </details>
    </div>
  );
}
```

## State Management

### Render Store (Zustand)

```typescript
// src/stores/renderStore.ts

interface RenderState {
  // Job list
  jobs: RenderJob[];
  activeJobs: RenderJob[];
  pendingJobs: RenderJob[];
  completedJobs: RenderJob[];

  // Queue status
  queueStatus: RenderQueueStatus | null;

  // Encoder info
  encoders: EncoderInfo[];
  formats: OutputFormatInfo[];
  hwAccelAvailable: boolean;

  // Modal state
  showStartModal: boolean;
  selectedProjectId: string | null;

  // Actions
  fetchJobs: () => Promise<void>;
  fetchQueueStatus: () => Promise<void>;
  fetchEncoders: () => Promise<void>;
  fetchFormats: () => Promise<void>;
  startRender: (projectId: string, settings: RenderSettings) => Promise<void>;
  cancelRender: (jobId: string) => Promise<void>;
  retryRender: (jobId: string) => Promise<void>;
  deleteRender: (jobId: string) => Promise<void>;
  openStartModal: (projectId?: string) => void;
  closeStartModal: () => void;

  // WebSocket update handlers
  onRenderQueued: (event: RenderQueuedEvent) => void;
  onRenderStarted: (event: RenderStartedEvent) => void;
  onRenderProgress: (event: RenderProgressEvent) => void;
  onRenderCompleted: (event: RenderCompletedEvent) => void;
  onRenderFailed: (event: RenderFailedEvent) => void;
  onRenderCancelled: (event: RenderCancelledEvent) => void;
}
```

### WebSocket Event Handling

Extend the existing `useWebSocket` hook to handle Phase 5 events:

```typescript
// src/hooks/useWebSocket.ts (additions)

case 'render.queued':
  useRenderStore.getState().onRenderQueued(event);
  break;
case 'render.started':
  useRenderStore.getState().onRenderStarted(event);
  break;
case 'render.progress':
  useRenderStore.getState().onRenderProgress(event);
  break;
case 'render.completed':
  useRenderStore.getState().onRenderCompleted(event);
  break;
case 'render.failed':
  useRenderStore.getState().onRenderFailed(event);
  break;
case 'render.cancelled':
  useRenderStore.getState().onRenderCancelled(event);
  break;
case 'render.frame_available':
  // Handled by RenderFrameDisplay component subscription
  break;
case 'render.queue_status':
  useRenderStore.getState().fetchQueueStatus();
  break;
```

## Theater Mode Integration

Phase 4's AI Theater Mode shows render progress. Phase 5 enriches this with real render data and live rendered frame display via the `render.frame_available` WebSocket event. When a render is active, Theater Mode fetches the latest rendered frame (540p JPEG via proxy quality infrastructure) and displays it alongside progress stats.

```typescript
// Updates to theater mode (Phase 4 components)

// BottomHUD gains render-specific info when a render is active
function BottomHUD() {
  const { renderProgress } = usePreviewStore();  // existing from Phase 4
  const { activeJobs } = useRenderStore();         // new Phase 5 data

  // When a render is active, show its real progress instead of preview progress
  const displayJob = activeJobs[0];  // most recent active render

  return (
    <div data-testid="theater-bottom-hud">
      {displayJob && (
        <div className="text-white/80 text-sm">
          Rendering: {(displayJob.progress * 100).toFixed(0)}%
          | {displayJob.fps.toFixed(0)} fps
          | ETA: {formatETA(displayJob.eta_seconds)}
          | {displayJob.encoder}{displayJob.hardware_accelerated ? ' (HW)' : ''}
        </div>
      )}
      {/* existing playback controls */}
    </div>
  );
}

// RenderFrameDisplay shows the latest rendered frame in Theater Mode
function RenderFrameDisplay({ jobId }: { jobId: string }) {
  const [frameUrl, setFrameUrl] = useState<string | null>(null);

  // Listen for render.frame_available WebSocket events
  useEffect(() => {
    const handler = (event: RenderFrameAvailableEvent) => {
      if (event.job_id === jobId) {
        setFrameUrl(event.frame_data_url);
      }
    };
    subscribeToEvent('render.frame_available', handler);
    return () => unsubscribeFromEvent('render.frame_available', handler);
  }, [jobId]);

  if (!frameUrl) return null;

  return (
    <img
      data-testid="render-frame-preview"
      src={frameUrl}
      alt="Latest rendered frame"
      className="w-full h-auto"
    />
  );
}
```

## Component File Structure

```
gui/src/
├── components/
│   ├── render/
│   │   ├── RenderControlCenter.tsx     # main render page layout
│   │   ├── RenderJobCard.tsx           # individual job display
│   │   ├── RenderProgressBar.tsx       # progress bar with ETA
│   │   ├── RenderQueueStatus.tsx       # queue overview bar
│   │   ├── ActiveRenderList.tsx        # active jobs section
│   │   ├── PendingRenderList.tsx       # pending queue section
│   │   ├── RenderHistory.tsx           # completed/failed history
│   │   ├── StartRenderModal.tsx        # render start dialog
│   │   ├── RenderSettingsForm.tsx      # format/quality/encoder form
│   │   ├── EncoderSelector.tsx         # HW/SW encoder radio group
│   │   ├── QualityPresetSelector.tsx   # draft/medium/high/lossless
│   │   ├── OutputPathSelector.tsx      # output path with browse
│   │   ├── DiskSpaceIndicator.tsx      # free space check display
│   │   ├── CommandPreview.tsx          # FFmpeg command preview
│   │   └── StatusBadge.tsx             # status color badge
│   │
│   ├── preview/    # existing (Phase 4, no changes)
│   └── theater/    # existing (Phase 4, minor additions)
│       └── BottomHUD.tsx               # EXTEND - render progress display
│
├── stores/
│   └── renderStore.ts                  # render jobs + queue state
│
├── hooks/
│   ├── useRenderEstimate.ts            # disk space + size estimation
│   └── useCommandPreview.ts            # FFmpeg command preview
│
├── api/
│   └── render.ts                       # render REST API client
│
└── types/
    └── render.ts                       # RenderJob, RenderSettings, etc.
```

## Navigation Updates

Add Render tab to the navigation bar:

```
[Dashboard] [Library] [Projects] [Effects] [Timeline] [Preview] [Render]
```

Render page shows the Render Control Center. The "Start Render" button is also accessible from the Timeline page header as a quick action.
