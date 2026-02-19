# Requirements: live-filter-preview

## Goal

Build debounced filter string preview panel with syntax highlighting and copy-to-clipboard.

## Background

Backlog Item: BL-050

M2.8 specifies showing the Rust-generated FFmpeg filter string in real time as users adjust effect parameters. This is the core transparency feature — users see exactly what commands Rust generates. The preview uses debounced API calls (300ms, matching existing useDebounce convention) to avoid excessive requests while parameter values change.

## Functional Requirements

**FR-001**: Filter string panel displays the current FFmpeg filter and updates on parameter change
- AC: Monospace panel renders the filter string
- AC: Updates automatically when effectFormStore parameter values change
- AC: Shows loading indicator during API call
- AC: Shows error state if preview API fails

**FR-002**: API calls to get filter preview are debounced to avoid excessive requests
- AC: Debounce interval is 300ms (matching existing useDebounce convention)
- AC: Rapid parameter changes result in a single API call after debounce
- AC: useEffectPreview hook manages debounced fetch

**FR-003**: FFmpeg filter syntax displayed with syntax highlighting
- AC: Filter names highlighted in a distinct color
- AC: Pad labels (e.g., `[0:v]`, `[out]`) highlighted in a distinct color
- AC: Key=value parameters in default text color
- AC: Simple regex-based coloring (not a full grammar)

**FR-004**: Copy-to-clipboard button copies the filter string for external use
- AC: Click on copy button copies the full filter string to clipboard
- AC: Visual feedback confirms copy action (tooltip or icon change)
- AC: Works in all supported browsers

## Non-Functional Requirements

**NFR-001**: Preview update latency < 500ms after debounce (excluding API latency)
- Metric: Component renders within 200ms of receiving API response

**NFR-002**: Keyboard accessible copy button
- Metric: Copy button reachable and activatable via keyboard

## Out of Scope

- Rendered video preview / thumbnail generation
- Filter string editing (read-only display)
- Multiple filter string formats

## Test Requirements

- ~1 Vitest test: FilterPreview renders filter string in monospace panel
- ~1 Vitest test: Debounce behavior verification (300ms)
- ~1 Vitest test: Syntax highlighting for filter names and pad labels
- ~1 Vitest test: Copy-to-clipboard click handler
- ~2 Vitest tests: effectPreviewStore filter string and loading state
- ~2 Vitest tests: useEffectPreview hook (debounced fetch, error handling)

See `comms/outbox/versions/design/v007/005-logical-design/test-strategy.md` for full test breakdown.

## Reference

See `comms/outbox/versions/design/v007/004-research/` for supporting evidence:
- `external-research.md`: FFmpeg syntax highlighting approach (simple regex coloring)
- `evidence-log.md`: Debounce interval 300ms
- `codebase-patterns.md`: useDebounce hook pattern