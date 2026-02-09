# Implementation Plan - 003: Library Browser

## Overview

Build the library browser with a video grid showing thumbnails, search with 300ms debounce, sort/filter controls, a scan modal, and virtual scrolling or pagination for large libraries. Consumes the thumbnail pipeline and pagination fix from Theme 02.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `gui/src/pages/LibraryPage.tsx` | Modify | Replace placeholder with full library browser |
| `gui/src/components/VideoGrid.tsx` | Create | Responsive video grid with thumbnail cards |
| `gui/src/components/VideoCard.tsx` | Create | Individual video card (thumbnail, name, duration) |
| `gui/src/components/SearchBar.tsx` | Create | Search input with 300ms debounce |
| `gui/src/components/SortControls.tsx` | Create | Sort by date/name/duration |
| `gui/src/components/ScanModal.tsx` | Create | Directory scan trigger modal |
| `gui/src/hooks/useVideos.ts` | Create | Video list/search API hook with pagination |
| `gui/src/hooks/useDebounce.ts` | Create | Generic debounce hook |
| `gui/src/stores/libraryStore.ts` | Create | Zustand store for library state |
| `gui/src/components/__tests__/VideoGrid.test.tsx` | Create | Video grid tests |
| `gui/src/components/__tests__/SearchBar.test.tsx` | Create | Search bar tests |
| `gui/src/components/__tests__/ScanModal.test.tsx` | Create | Scan modal tests |

## Implementation Stages

### Stage 1: Video Grid and Cards

1. Create `VideoCard.tsx`: display thumbnail image (from `/api/videos/{id}/thumbnail`), filename, and formatted duration
2. Create `VideoGrid.tsx`: responsive CSS Grid layout rendering `VideoCard` components
3. Create `useVideos` hook: fetch from `/api/v1/videos` with pagination params
4. Create `libraryStore` with Zustand for videos, search query, sort, and pagination state

**Verification:**
```bash
cd gui && npx vitest run
```

### Stage 2: Search and Sort

1. Create `useDebounce` hook with configurable delay (default 300ms)
2. Create `SearchBar.tsx`: input field using debounce hook, calls `/api/videos/search` on debounced value change
3. Create `SortControls.tsx`: dropdown/buttons for sort by date, name, duration
4. Wire search and sort to `libraryStore` and `useVideos` hook

**Verification:**
```bash
cd gui && npx vitest run
```

### Stage 3: Scan Modal and Large Library Handling

1. Create `ScanModal.tsx`: directory path input, submit button triggering `POST /api/v1/jobs` with scan payload
2. Show scan progress feedback (WebSocket events from Theme 01)
3. Implement virtual scrolling or pagination:
   - Evaluate `@tanstack/react-virtual` for grid virtualization
   - If grid support is insufficient, fall back to standard pagination with page controls
   - Use `total` from fixed pagination endpoint for page count calculation
4. Assemble all components in `LibraryPage.tsx`

**Verification:**
```bash
cd gui && npx vitest run
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest tests/
```

## Test Infrastructure Updates

- Vitest tests with mocked fetch for video API endpoints
- Vitest tests with mocked thumbnail URLs
- Vitest tests for debounce behavior with fake timers

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
cd gui && npx vitest run
```

## Risks

- **R-6 (Virtual scrolling):** Evaluate tanstack-virtual first. Pagination is an acceptable fallback per BL-033 AC#5. CSS Grid with Intersection Observer is a third option for <500 items.

See `comms/outbox/versions/design/v005/006-critical-thinking/risk-assessment.md`.

## Commit Message

```
feat: build library browser with video grid, search, and scan

- Create video grid with thumbnail cards and responsive layout
- Add search bar with 300ms debounce calling /api/videos/search
- Add sort controls for date, name, duration ordering
- Implement scan modal triggering directory scan via jobs API
- Add virtual scrolling or pagination for large libraries

Implements BL-033
```