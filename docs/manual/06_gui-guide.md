# GUI Guide

Stoat & Ferret includes a web-based GUI built with React. It provides a visual interface for managing videos, projects, and effects without writing API calls.

## Accessing the GUI

Start the server and open your browser to:

```
http://localhost:8000/gui/
```

The GUI is served as static files from the `gui/dist` directory. The path is configurable via the `STOAT_GUI_STATIC_PATH` environment variable.

> **SPA Routing Note:** The GUI is a single-page application (SPA) using React Router. Always navigate to `/gui/` first and then use the in-app navigation links. Directly entering sub-page URLs (e.g., `/gui/library`) in the browser address bar may not work correctly because the server-side SPA fallback has a known limitation. Once you are on `/gui/`, all in-app navigation works as expected.

## Pages

The GUI has four main pages accessible from the navigation:

| Page | URL | Description |
|------|-----|-------------|
| Dashboard | `/gui/` | System health and metrics overview |
| Library | `/gui/library` | Video library browser with search and scan |
| Projects | `/gui/projects` | Project management |
| Effects | `/gui/effects` | Effect Workshop for configuring and applying effects |

---

## Dashboard

The Dashboard is the landing page and provides an at-a-glance view of system status:

- **Health Status** -- Shows the result of the readiness check (database and FFmpeg health)
- **Metrics Overview** -- Key operational metrics from the Prometheus endpoint
- **Quick Actions** -- Links to common tasks like scanning for videos or creating a project

The health information mirrors what you would see from `GET /health/ready`.

---

## Library

The Library page is your video collection browser.

### Browsing Videos

Videos are displayed in a paginated list or grid showing:

- Thumbnail preview
- Filename
- Resolution (width x height)
- Duration
- Codec information
- File size

### Searching

Use the search bar to filter videos by filename or path. This calls the `GET /api/v1/videos/search` endpoint.

### Scanning for Videos

To add new videos to the library:

1. Use the Scan button or form on the Library page
2. Enter the directory path containing your video files
3. Choose whether to scan recursively (include subdirectories)
4. Submit the scan

The scan runs in the background as an async job. The UI shows the scan progress and results when complete, indicating how many new, updated, and skipped files were found.

### Video Details

Click on a video to see its full metadata:

- File path
- Duration in frames and the corresponding frame rate
- Video codec and resolution
- Audio codec (if present)
- File size
- Generated thumbnail

---

## Projects

The Projects page lets you create and manage editing projects.

### Creating a Project

1. Click the "New Project" button
2. Enter a project name
3. Configure output settings:
   - **Width** (default: 1920)
   - **Height** (default: 1080)
   - **FPS** (default: 30)
4. Submit to create the project

### Project View

Select a project to see its details and timeline:

- Project metadata (name, output settings, timestamps)
- List of clips on the timeline
- Each clip shows its source video, in/out points, timeline position, and applied effects

### Managing Clips

From the project view, you can:

- **Add clips** by selecting a video from the library and specifying frame-based in/out points and timeline position
- **Update clips** by modifying their in_point, out_point, or timeline_position
- **Remove clips** from the timeline

All clip operations validate through the Rust core before being saved.

---

## Effect Workshop

The Effect Workshop (`/gui/effects`) is an interactive tool for discovering, configuring, and applying effects to clips. It uses Zustand stores for state management and is composed of several components.

### Clip Selector

Choose which clip to work with. The selector shows clips from your project with their source video information and current timeline position.

### Effect Catalog

Browse all 9 available effects:

| Effect | Description |
|--------|-------------|
| Text Overlay | Add text with font, color, and position controls |
| Speed Control | Adjust playback speed (0.25x to 4.0x) |
| Volume | Adjust audio volume level |
| Audio Fade | Fade audio in or out |
| Video Fade | Fade video in or out with configurable color |
| Audio Mix | Mix multiple audio streams |
| Audio Ducking | Lower music during speech |
| Crossfade (Video) | Video transition between clips (xfade) |
| Crossfade (Audio) | Audio transition between clips (acrossfade) |

Each effect card shows the name, description, and a summary of its parameters.

### Effect Parameter Form

After selecting an effect, the Parameter Form renders appropriate input controls based on the effect's JSON schema:

- **Text fields** for string parameters
- **Number inputs** with min/max constraints for numeric parameters
- **Dropdowns** for enum parameters (e.g., position presets, fade curves)
- **Toggles** for boolean parameters
- **Default values** are pre-filled from the schema

Required parameters are clearly marked. The form validates inputs against the schema before submission.

### Filter Preview

As you configure parameters, the Filter Preview panel shows the FFmpeg filter string that would be generated. This calls the `POST /api/v1/effects/preview` endpoint in real time, letting you verify the output before applying.

Example preview output:
```
drawtext=text='Hello World':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=h-text_h-20
```

### Effect Stack

The Effect Stack panel shows all effects currently applied to the selected clip. For each effect in the stack, you can:

- **View** the effect type, parameters, and generated filter string
- **Edit** parameters (opens the Parameter Form with current values)
- **Delete** the effect from the stack

Effects are displayed in application order (the order they appear in the clip's `effects` array).

### Workflow Example

A typical Effect Workshop workflow:

1. Navigate to `/gui/effects` (use in-app navigation)
2. Select a clip from the Clip Selector
3. Browse the Effect Catalog and select "Video Fade"
4. Configure parameters: fade_type = "in", duration = 1.5
5. Preview the filter string in the Filter Preview panel
6. Click "Apply" to add the effect to the clip
7. See the effect appear in the Effect Stack
8. Select "Text Overlay" from the catalog
9. Configure: text = "My Video", position = "bottom_center"
10. Apply to build up the effect stack

---

## Planned GUI Features

The following features are planned but not yet implemented:

- **[Planned] Theater Mode** -- Full-screen preview with playback controls for reviewing clips and effects in context
- **[Planned] Timeline Canvas** -- Visual timeline with drag-and-drop clip arrangement, similar to traditional video editors
- **[Planned] Preview Player** -- In-browser video preview with real-time effect rendering
- **[Planned] Render Panel** -- Export configuration and render progress monitoring

## Next Steps

- [Effects Guide](04_effects-guide.md) -- detailed effect parameters and curl examples
- [Timeline Guide](05_timeline-guide.md) -- frame-based clip management
- [AI Integration](08_ai-integration.md) -- programmatic control for AI workflows
