# 03 — User Journeys

Seven end-user flows that the UAT script validates. Each journey represents a critical path a real user would follow.

---

## Journey 1: Application Boot & Health Check

**Goal:** Verify the app compiles, starts, and the GUI is reachable.

**Priority:** P0 — if this fails, nothing else can run.

### Steps

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 1 | Build Rust core via `maturin develop` | Build succeeds, exit code 0 |
| 2 | Install Python dependencies | `pip install -e .` succeeds |
| 3 | Build React GUI (`npm run build` in `gui/`) | Build succeeds, `gui/dist/` populated |
| 4 | Start the application (`uvicorn`) | Server process starts |
| 5 | Open browser to `http://localhost:8765/gui/` | Page loads without error |
| 6 | Verify application shell renders | Navigation tabs visible in DOM |
| 7 | Verify health indicator shows green | Dashboard fetches `/health/ready`, indicator green |
| 8 | Verify all navigation tabs present | Dashboard, Library, Projects, Effects, Timeline tabs exist |

### Screenshot Checkpoints

- `01_app_shell_loaded.png` — Application shell with navigation tabs
- `02_health_green.png` — Health indicator showing green status

---

## Journey 2: Scan Video Library & Browse

**Goal:** A user scans a directory of videos and browses the results.

**Priority:** P0 — core library functionality, first thing a new user does.

### Steps

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 1 | Navigate to Library tab | Library page loads |
| 2 | Click "Scan Directory" button | Scan modal opens |
| 3 | Enter path to the `videos/` directory | Path appears in input |
| 4 | Click "Scan" to submit | Scan job starts |
| 5 | Wait for scan progress to complete | Modal shows progress → completion |
| 6 | Verify video grid populates with thumbnails | Grid shows video cards |
| 7 | Verify video cards show filename, duration, resolution | Card metadata present |
| 8 | Type a search query in the search box | Search input accepts text |
| 9 | Verify search results update (FTS5) | Grid filters to matching results |

### Screenshot Checkpoints

- `01_library_empty.png` — Empty library before scan
- `02_scan_modal_open.png` — Scan directory modal
- `03_scan_in_progress.png` — Scan progress indicator
- `04_library_populated.png` — Library with video grid populated
- `05_search_results.png` — Filtered search results

---

## Journey 3: Create Project & Add Clips

**Goal:** A user creates a new project and adds video clips to it.

**Priority:** P0 — core project workflow.

### Steps

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 1 | Navigate to Projects tab | Project list page loads |
| 2 | Click "+ New Project" button | Create project modal opens |
| 3 | Fill in project name ("UAT Test Project"), resolution (1920×1080), FPS (30) | Form fields populated |
| 4 | Click "Create" | Modal closes, project created |
| 5 | Verify project appears in project list | Project name visible in list |
| 6 | Click the project to view details | Project detail page loads |
| 7 | Verify clip list is initially empty | Empty clip list displayed |
| 8 | Add a clip to the project | Clip creation succeeds |
| 9 | Verify clip appears with correct source, in/out points, timeline position | Clip metadata correct |
| 10 | Add 2-3 more clips | Multiple clips created |
| 11 | Verify all clips listed with Rust-calculated timeline positions | Positions computed and displayed |

### Screenshot Checkpoints

- `01_project_list_empty.png` — Empty project list
- `02_create_modal.png` — Create project modal with fields filled
- `03_project_created.png` — Project visible in list
- `04_project_detail_with_clips.png` — Project detail page showing clips

---

## Journey 4: Apply Effects via Effect Workshop

**Goal:** A user applies, edits, and removes effects on clips.

**Priority:** P1 — key creative feature with complex UI interactions.

### Steps

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 1 | Navigate to Effects tab (`/gui/effects`) | Effects page loads |
| 2 | Select the project created in Journey 3 | Project selected |
| 3 | Select the first clip | Clip selected, effect panel appears |
| 4 | Browse the effect catalog | Effects listed (Text Overlay, Speed Control, etc.) |
| 5 | Click "Text Overlay" | Text Overlay parameter form opens |
| 6 | Fill parameters: text="Chapter 1", position=center, font_size=48 | Form fields populated |
| 7 | Verify filter preview shows FFmpeg drawtext filter string | Preview renders filter expression |
| 8 | Click "Apply Effect to Clip" | Effect applied |
| 9 | Verify effect appears in effect stack | Stack shows 1 effect |
| 10 | Click "Edit" on the applied effect | Edit form opens with current values |
| 11 | Change font_size to 64 | Field updated |
| 12 | Save — verify stack updates | Stack reflects updated parameter |
| 13 | Apply a second effect (Speed Control at 0.75x) | Second effect applied |
| 14 | Verify effect stack shows 2 effects | Stack count = 2 |
| 15 | Remove the speed control effect (two-step confirm) | Confirmation dialog, then removal |
| 16 | Verify stack shows 1 effect | Stack count = 1 |

### Screenshot Checkpoints

- `01_effect_catalog_loaded.png` — Effect catalog with listed effects
- `02_parameter_form_filled.png` — Text Overlay form with parameters
- `03_filter_preview.png` — FFmpeg filter string preview
- `04_effect_stack_one.png` — Effect stack with 1 effect
- `05_effect_stack_two.png` — Effect stack with 2 effects
- `06_after_removal.png` — Effect stack after removing one effect

---

## Journey 5: Timeline Visualization

**Goal:** A user views and interacts with the multi-track timeline.

**Priority:** P1 — visual correctness of the editor view.

### Steps

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 1 | Navigate to Timeline tab (`/gui/timeline`) | Timeline page loads |
| 2 | Verify timeline canvas loads with clips from project | Canvas populated with clip blocks |
| 3 | Verify time ruler is visible (0s, 5s, 10s, etc.) | Time ruler rendered |
| 4 | Verify clips appear as rectangular blocks on video track | Clip rectangles visible |
| 5 | Click a clip | Clip becomes selected (blue border/highlight) |
| 6 | Verify clip properties panel shows duration, position, effects | Properties panel populated |
| 7 | Use zoom controls | Timeline scale changes |
| 8 | Scroll horizontally | Panning works, different portion visible |
| 9 | Verify effect overlays/markers on clips with effects | Markers or indicators present |

### Screenshot Checkpoints

- `01_timeline_loaded.png` — Timeline canvas with clips
- `02_clip_selected.png` — Selected clip with properties panel
- `03_zoomed_in.png` — Timeline at increased zoom level
- `04_zoomed_out.png` — Timeline at decreased zoom level

---

## Journey 6: Layout Composition

**Goal:** A user selects layout presets and views the composition preview.

**Priority:** P2 — less critical, depends on multi-track projects.

### Steps

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 1 | On Timeline page, locate layout presets section | Layout presets visible |
| 2 | Click "Side-by-Side" preset | Preset selected |
| 3 | Verify 16:9 layout preview shows two rectangles | Side-by-side layout rendered |
| 4 | Click "PIP Top-Left" preset | Preset selected |
| 5 | Verify preview shows small rectangle at top-left, large below | PIP layout rendered |
| 6 | Click "Grid 2x2" preset | Preset selected |
| 7 | Verify preview shows four rectangles in 2×2 grid | Grid layout rendered |

### Screenshot Checkpoints

- `01_side_by_side.png` — Side-by-Side layout preview
- `02_pip_top_left.png` — PIP Top-Left layout preview
- `03_grid_2x2.png` — Grid 2×2 layout preview

---

## Journey 7: Seed Sample Project & Verify

**Goal:** The canonical "Running Montage" sample project loads and displays correctly throughout the app.

**Priority:** P1 — regression safety net for the canonical project.

### Steps

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 1 | Run `scripts/seed_sample_project.py` against running instance | Seed completes, exit code 0 |
| 2 | Navigate to Projects tab | Projects page loads |
| 3 | Verify "Running Montage" appears in project list | Project name visible |
| 4 | Click the project | Project detail page loads |
| 5 | Verify 4 clips are listed | Clip count = 4 |
| 6 | Navigate to Effects — select the project | Effects page loads with project |
| 7 | Verify effects are applied to clips | Effect indicators present |
| 8 | Navigate to Timeline | Timeline page loads |
| 9 | Verify all 4 clips appear on timeline with correct durations | 4 clip blocks with durations |
| 10 | Verify transition between clips 1→2 is represented in UI | Transition indicator visible |

### Screenshot Checkpoints

- `01_sample_project_in_list.png` — Running Montage in project list
- `02_clip_details.png` — 4 clips with details
- `03_effects_on_clips.png` — Effects applied to clips
- `04_full_timeline.png` — Complete timeline view with all clips and transition

---

## Priority Summary

| Priority | Journey | Rationale |
|----------|---------|-----------|
| P0 | 1: Boot & Health | If this fails, nothing else can run |
| P0 | 2: Scan & Browse | Core library functionality, first user action |
| P0 | 3: Create Project & Clips | Core project workflow |
| P1 | 4: Apply Effects | Key creative feature, complex UI |
| P1 | 5: Timeline | Visual correctness of the editor |
| P2 | 6: Layout Composition | Less critical, depends on multi-track |
| P1 | 7: Sample Project | Regression safety net |
