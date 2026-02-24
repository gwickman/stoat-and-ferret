# External Research: v011

## BL-070 — Folder Picker Mechanism

### File System Access API (`showDirectoryPicker()`)

**Browser Support (as of Feb 2026):**
- Chrome 86+, Edge 86+, Opera 72+: Supported
- Firefox: **Not supported**
- Safari: **Not supported**

**Source:** [MDN Web Docs — showDirectoryPicker()](https://developer.mozilla.org/en-US/docs/Web/API/Window/showDirectoryPicker), [Can I Use](https://caniuse.com/mdn-api_window_showdirectorypicker)

**Assessment:** Not viable as the sole mechanism. This project's GUI needs to work across browsers. The API is experimental and Chromium-only.

### Recommended Approach: Backend-Assisted Directory Listing

Since browser-native folder picking is unreliable, the recommended approach is a backend endpoint:

**Proposed endpoint:** `GET /api/v1/filesystem/directories?path={parent_path}`
- Returns list of subdirectories within the given parent path
- Respects `allowed_scan_roots` security setting for path restriction
- Frontend renders a tree/list browser component
- User navigates and selects, path populates the input field

**Precedent:** The existing scan endpoint already validates paths against `allowed_scan_roots` (`src/stoat_ferret/api/routers/videos.py:194-200`). The directory listing endpoint can reuse this security pattern.

**LRN-029 application (Conscious Simplicity):** Start with a flat directory listing (one level at a time). Document upgrade path: when `showDirectoryPicker()` reaches Firefox/Safari, add client-side detection to use native picker when available and fall back to backend listing.

### Polyfill Option (Evaluated, Not Recommended)

[file-system-access polyfill](https://github.com/nicolo-ribaudo/browser-fs-access) provides a fallback using `<input>` elements, but it cannot return directory paths — only file handles. This doesn't solve the "select a directory" use case.

## BL-075 — Zustand Store Patterns

### DeepWiki Research: pmndrs/zustand

**Source:** DeepWiki query on `pmndrs/zustand`

**Recommended patterns for v011:**

1. **Independent stores (project's existing pattern):** Each feature gets its own `create<T>()` store. This matches the project's 7 existing stores in `gui/src/stores/`. BL-075 should create a `clipStore.ts` following this pattern.

2. **Async actions:** Define async functions within the store that call `set()` on completion. No middleware needed. Example from project: `effectStackStore.ts` uses `fetchEffects: async (projectId, clipId) => { set({ isLoading: true }); ... }`.

3. **Composition:** Zustand's "slices pattern" allows composing stores, but the project uses fully independent stores — each consumed directly by components. This is simpler and sufficient for v011's scope.

**Recommendation:** Follow the established independent-store pattern. Do not introduce the slices pattern; it would break consistency with existing code.

## BL-076 — Impact Assessment File Format

### Auto-dev Framework Expectation

**Source:** `docs/auto-dev/PROMPTS/design_version_prompt/task_prompts/003-impact-assessment.md`

The auto-dev design phase (Task 003) reads `docs/auto-dev/IMPACT_ASSESSMENT.md` when it exists and executes project-specific checks. The file should contain structured check sections that a Claude Code agent can parse and execute during design review.

**Format recommendation:** Each check should include:
- **Check name** (heading)
- **What to look for** (specific grep patterns, file patterns, or review criteria)
- **Why it matters** (1-2 sentences linking to project history)
- **Concrete example** (file paths, line numbers, what happened)

## BL-071 — Pydantic BaseSettings .env Pattern

### Standard Pattern

Pydantic `BaseSettings` with `SettingsConfigDict(env_file=".env")` is the established pattern. The `.env.example` file should:
- List all environment variables with their `STOAT_` prefix
- Include comments explaining each variable's purpose
- Show default values (matching the Settings class defaults)
- Group by category (database, API, logging, security, frontend)

The project already uses this pattern correctly in `settings.py`. No external research needed — the implementation is standard.
