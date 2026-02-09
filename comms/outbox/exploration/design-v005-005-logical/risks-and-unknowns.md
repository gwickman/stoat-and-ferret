# Risks and Unknowns — v005

## Risks

### R-1: Framework selection locks in long-term technology choice
- **Severity:** High
- **Description:** Choosing React over Svelte is a significant decision that affects all future GUI development. The recommendation is based on ecosystem size and design doc alignment, but the team has no existing frontend code to validate either choice.
- **Investigation:** Review 08-gui-architecture.md for framework-specific patterns. Confirm JSX/hooks/Zustand patterns are present and not just illustrative. Verify no Svelte-specific requirements exist elsewhere.
- **Current best guess:** React is the right choice — design docs are React-aligned, ecosystem is larger, virtual scrolling library options are better.

### R-2: FastAPI StaticFiles `html=True` SPA routing may not handle all edge cases
- **Severity:** Medium
- **Description:** The `html=True` flag on `StaticFiles` provides basic SPA fallback but may not handle all client-side routing patterns (e.g., deep nested routes, routes that look like file paths). A custom `SPAStaticFiles` subclass may be needed.
- **Investigation:** Test with React Router's `BrowserRouter` using nested routes like `/gui/library/search?q=test`. Verify fallback serves `index.html` for these paths.
- **Current best guess:** `html=True` should suffice for the v005 route structure (flat tabs: `/gui/`, `/gui/library`, `/gui/projects`). Custom handler is a documented fallback if needed.

### R-3: WebSocket connection stability in long-running sessions
- **Severity:** Medium
- **Description:** WebSocket connections can drop due to proxies, NAT timeouts, or browser backgrounding. The heartbeat mechanism (30s interval) may not be sufficient in all deployment environments.
- **Investigation:** Test with browser tab backgrounded for extended periods. Verify reconnection logic handles stale connections gracefully.
- **Current best guess:** 30s heartbeat with client-side reconnection logic will handle most cases. This is a locally-served app (not behind load balancers), reducing proxy-related risks.

### R-4: Thumbnail generation performance for large libraries
- **Severity:** Medium
- **Description:** Generating thumbnails during scan could slow down the scan pipeline significantly for large libraries (100+ videos). FFmpeg extraction takes ~1-2s per video.
- **Investigation:** Benchmark thumbnail generation time per video. Consider async generation (generate thumbnails in background after scan completes) if scan time is unacceptable.
- **Current best guess:** On-scan generation is acceptable for v005 (single-user local app with typical library sizes). Lazy fallback noted in research (UQ-3).

### R-5: Vitest and Playwright CI integration adds significant build time
- **Severity:** Low
- **Description:** Adding Node.js setup, npm install, Vite build, Vitest, and Playwright browser installation to CI could significantly increase pipeline duration.
- **Investigation:** Measure CI run time after Theme 01. Consider caching `node_modules/` and Playwright browsers.
- **Current best guess:** CI time increase is manageable. LRN-015 suggests running expensive operations on single platform (ubuntu-latest only for Playwright).

### R-6: Virtual scrolling library compatibility with video grid layout
- **Severity:** Low
- **Description:** Virtual scrolling for the library browser (BL-033 AC#5) requires a library that supports grid layout (not just list). Options include react-window, react-virtuoso, tanstack-virtual — each has different grid support levels.
- **Investigation:** Evaluate grid support in each library during BL-033 implementation. Consider CSS Grid with intersection observer as alternative.
- **Current best guess:** tanstack-virtual or react-virtuoso support grid layouts. Decision deferred to implementation per UQ-2.

---

## Unknowns

### UQ-1: WebSocket heartbeat optimal interval
- **Severity:** Low
- **Description:** The 30s default is an industry standard but may need tuning based on actual deployment characteristics.
- **Resolution path:** Start with 30s, make configurable via `STOAT_WS_HEARTBEAT_INTERVAL`. Monitor in practice.

### UQ-2: Virtual scrolling library choice
- **Severity:** Medium
- **Description:** Multiple React virtual scrolling libraries exist with different API styles and grid support. The choice affects the library browser implementation significantly.
- **Resolution path:** Evaluate react-window, react-virtuoso, and tanstack-virtual during BL-033 feature design. Consider grid layout requirements, TypeScript support, and bundle size.

### UQ-3: Thumbnail generation timing (on-scan vs on-first-access)
- **Severity:** Low
- **Description:** Generating thumbnails during scan adds latency to scan operations. On-first-access defers work but creates a cold-start experience for users browsing the library.
- **Resolution path:** Implement on-scan (simpler, eager). If scan performance degrades for large libraries, add lazy generation as fallback. BL-032 AC#1 allows either: "generated during video scan or on first access."

### UQ-4: Frontend test coverage baseline
- **Severity:** Low
- **Description:** No existing frontend code means no baseline for coverage thresholds. Setting too high a threshold initially may slow feature development.
- **Resolution path:** Start without enforced threshold (LRN-013). Establish baseline after Theme 03 completes. Ratchet up in subsequent versions.

---

## Risk Summary

| ID | Description | Severity | Theme Affected |
|----|-------------|----------|----------------|
| R-1 | Framework selection permanence | High | 01 |
| R-2 | SPA routing edge cases | Medium | 01 |
| R-3 | WebSocket connection stability | Medium | 01, 03 |
| R-4 | Thumbnail generation performance | Medium | 02 |
| R-5 | CI build time increase | Low | 01, 04 |
| R-6 | Virtual scrolling library compatibility | Low | 03 |
| UQ-1 | WebSocket heartbeat interval | Low | 01 |
| UQ-2 | Virtual scrolling library choice | Medium | 03 |
| UQ-3 | Thumbnail generation timing | Low | 02 |
| UQ-4 | Frontend coverage baseline | Low | 04 |
