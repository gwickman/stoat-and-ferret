# Evidence Log: v011

## Clip CRUD Endpoint Existence

- **Value**: All 4 endpoints (GET/POST/PATCH/DELETE) exist and are integration-tested
- **Source**: `src/stoat_ferret/api/routers/projects.py` lines 212-412
- **Data**: GET (line 212), POST (line 245), PATCH (line 313), DELETE (line 385). Pydantic models in `src/stoat_ferret/api/schemas/clip.py`.
- **Rationale**: Confirms BL-075 is frontend-only work; no backend changes needed

## Clip Schema Fields (No Label Field)

- **Value**: ClipCreate has 4 fields: `source_video_id`, `in_point`, `out_point`, `timeline_position`. No `label` field.
- **Source**: `src/stoat_ferret/api/schemas/clip.py` lines 11-17
- **Data**: ClipUpdate also has no label field (lines 20-25). ClipResponse has no label field (lines 28-41).
- **Rationale**: BL-075 AC3 references "label" but the backend schema doesn't support it. Design must either: (a) adjust AC to reference actual fields, or (b) add a label field to the backend (scope creep).

## Settings Field Count

- **Value**: 11 fields total (10 configurable + `allowed_scan_roots` list)
- **Source**: `src/stoat_ferret/api/settings.py` lines 13-102
- **Data**: `database_path`, `api_host`, `api_port`, `debug`, `log_level`, `thumbnail_dir`, `gui_static_path`, `ws_heartbeat_interval`, `log_backup_count`, `log_max_bytes`, `allowed_scan_roots`
- **Rationale**: Config docs cover only 9; `.env.example` must include all 11

## showDirectoryPicker Browser Support

- **Value**: Chromium-only (Chrome 86+, Edge 86+). No Firefox or Safari support.
- **Source**: [MDN](https://developer.mozilla.org/en-US/docs/Web/API/Window/showDirectoryPicker), [Can I Use](https://caniuse.com/mdn-api_window_showdirectorypicker)
- **Data**: API is experimental, not on standards track for Firefox/Safari
- **Rationale**: Backend-assisted directory listing is the reliable approach for BL-070

## Zustand Store Count

- **Value**: 7 independent stores in `gui/src/stores/`
- **Source**: Glob of `gui/src/stores/*.ts`
- **Data**: projectStore, effectStackStore, effectCatalogStore, effectFormStore, effectPreviewStore, libraryStore, activityStore
- **Rationale**: Confirms LRN-037 pattern is active. New clipStore should follow same pattern.

## allowed_scan_roots Security Pattern

- **Value**: Path validation against configurable allowlist, empty list permits all
- **Source**: `src/stoat_ferret/api/routers/videos.py` lines 194-200, `settings.py` field `allowed_scan_roots: list[str] = []`
- **Data**: Returns 403 if path not within any allowed root. Can be reused for directory listing endpoint.
- **Rationale**: BL-070's new directory listing endpoint must respect this security boundary

## Historical Session Durations (Feature Implementation)

- **Value**: v010 feature sessions ranged 590-1131 seconds (10-19 minutes)
- **Source**: query_cli_sessions (session_list, project scope). Source: query_cli_sessions
- **Data**: BL-075-comparable full-stack feature (job cancellation, session ec571021): 1131s, 88 tool calls. BL-070-comparable (ScanModal-level, session 110039ea): 591s, 54 tool calls.
- **Rationale**: BL-075 (clip CRUD GUI) is larger scope than job cancellation — expect 15-25 min per feature. BL-070 is comparable to moderate features.

## Tool Reliability Risks

- **Value**: WebFetch has 35.7% error rate (30/84 calls failed). Edit has 9.7% error rate.
- **Source**: query_cli_sessions (tool_usage, 60 days). Source: query_cli_sessions
- **Data**: WebFetch: 84 calls, 30 errors. Edit: 2495 calls, 242 errors. DeepWiki: 46 calls, 6 errors (13%). Bash: 15887 calls, 2326 errors (14.6%).
- **Rationale**: WebFetch unreliability is known (PR-003 filed). Edit errors are likely retries on unique-match failures. No tool reliability risk specific to v011 features.

## Ruff ASYNC Rules

- **Value**: `["E", "F", "I", "UP", "B", "SIM", "ASYNC"]` — ASYNC rules enabled
- **Source**: `pyproject.toml` lint config
- **Data**: Added in v010 after ffprobe blocking bug RCA. Catches subprocess.run/call/check_output in async functions.
- **Rationale**: BL-076's async safety check supplements this CI gate with a design-time check

## nul Entry in .gitignore

- **Value**: Present at line 219
- **Source**: `.gitignore`
- **Data**: `nul` entry exists, confirming BL-019's note that "the .gitignore half is already done"
- **Rationale**: BL-019 scope is AGENTS.md documentation only
