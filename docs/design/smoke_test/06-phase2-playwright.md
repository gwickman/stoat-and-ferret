# Phase 2: Playwright E2E Tests

Phase 2 adds browser-level end-to-end tests using Playwright, providing full confidence that the React GUI works correctly with the backend. This phase should begin once the GUI feature set stabilizes (after Phase 3 of the roadmap is underway).

## Technology Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| Browser automation | Playwright | Multi-browser: Chromium, Firefox, WebKit |
| Test runner | `@playwright/test` | Built-in assertions, retries, parallel execution |
| Assertions | Playwright `expect` + API assertions | DOM, network, WebSocket |
| Application startup | `webServer` config in `playwright.config.ts` | Auto-starts uvicorn, waits for port |
| Test data | Real video files from `/videos/` | Same files used by Phase 1 smoke tests |
| Test selectors | `data-testid` attributes | Already present on all 27 React components |

## Application Startup

```typescript
// gui/playwright.config.ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  retries: process.env.CI ? 1 : 0,
  workers: 1,  // Sequential — tests share a server

  webServer: {
    command: 'cd ../.. && uv run uvicorn stoat_ferret.api.app:create_app --factory --host 127.0.0.1 --port 8765',
    port: 8765,
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },

  use: {
    baseURL: 'http://127.0.0.1:8765/gui/',
    trace: 'on-first-retry',
    video: 'retain-on-failure',
  },
});
```

Readiness detection: Playwright's `webServer` config automatically polls the port until it accepts connections. The first test step should additionally verify `GET /health/ready` returns 200.

## Automated Use Cases (9 Tests)

| Priority | Use Case | Test File | What It Verifies |
|----------|----------|-----------|------------------|
| 1 | System Health | `health-check.spec.ts` | Navigate to dashboard, assert health cards show "healthy", verify metrics cards display values |
| 2 | Scan Directory | `scan-directory.spec.ts` | Open scan modal via "Scan Directory" button, enter path, start scan, wait for progress bar to complete, verify video count updates |
| 3 | Browse Library | `library-browse.spec.ts` | Search for a video by name, verify filtered results, test sort controls, verify pagination displays correct counts |
| 4 | Create Project | `create-project.spec.ts` | Open CreateProjectModal, fill name/resolution/fps form, submit, verify project appears in project list |
| 5 | Add Clips | `add-clips.spec.ts` | Select a project, open ClipFormModal, search and select a video, set in/out points, submit, verify clip appears in clips table |
| 6 | Apply Effect | `apply-effect.spec.ts` | Navigate to Effects page, select project and clip, choose "Text Overlay" from catalog, configure parameters, verify filter preview text updates, apply, verify in effect stack |
| 7 | Edit Effect | `edit-effect.spec.ts` | Click "Edit" on an effect in the stack, modify parameters, verify filter preview updates, click "Update", verify stack shows new values |
| 8 | Apply Transition | `apply-transition.spec.ts` | Switch to Transitions tab, select adjacent clips, choose "Crossfade", set duration, verify filter preview shows xfade filter, apply |
| 9 | Delete Flows | `delete-flows.spec.ts` | Remove an effect (two-step confirmation), delete a clip (confirmation dialog), delete a project (confirmation dialog), verify each disappears from the UI |

## Result Verification Methods

| Method | Usage | Details |
|--------|-------|---------|
| **DOM assertions via `data-testid`** | All tests | `page.getByTestId('video-card')`, `expect(locator).toHaveText(...)` |
| **API response interception** | Scan, effects | `page.route('/api/v1/**', ...)` to capture and verify response bodies |
| **WebSocket events** | Dashboard, scan | Verify activity log updates after operations via DOM observation |
| **Filter preview text** | Effects, transitions | Assert filter preview container contains expected FFmpeg filter substrings |
| **Visual regression (optional)** | Key screens | `expect(page).toHaveScreenshot()` for dashboard, library grid, effects page |

All React components include `data-testid` attributes (e.g., `data-testid="scan-button"`, `data-testid="video-card"`, `data-testid="effect-stack-item"`), enabling stable selectors that don't break when CSS classes or element structure changes.

## CI Job Definition

```yaml
  playwright-tests:
    name: Playwright E2E
    runs-on: ubuntu-latest
    needs: [smoke-tests]  # Run after API-level smoke tests pass
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Set up FFmpeg
        uses: AnimMouse/setup-ffmpeg@v1

      - name: Set up Rust
        uses: dtolnay/rust-toolchain@stable

      - name: Install uv
        uses: astral-sh/setup-uv@v3

      - name: Install Python dependencies
        run: uv sync

      - name: Build Rust extension
        run: uv run maturin develop

      - name: Install GUI dependencies
        run: cd gui && npm ci

      - name: Build GUI
        run: cd gui && npm run build

      - name: Install Playwright browsers
        run: cd gui && npx playwright install --with-deps chromium

      - name: Run Playwright tests
        run: cd gui && npx playwright test
        timeout-minutes: 10

      - name: Upload test report
        uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: gui/playwright-report/
          retention-days: 7

      - name: Upload test videos
        uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-videos
          path: gui/test-results/
          retention-days: 7
```

### Key Differences from Phase 1 CI

- **Requires Node.js** — for Playwright browser binaries and test runner
- **Requires GUI build** — `npm ci && npm run build` to produce the static files served by FastAPI
- **Browser download** — `npx playwright install --with-deps chromium` (~100MB, adds ~1 min to CI)
- **Longer timeout** — 10 minutes (browser tests are slower than API tests)
- **Artifact uploads** — HTML report and video recordings preserved on failure for debugging
- **Depends on smoke-tests** — runs only after API-level tests pass (no point running browser tests if the API is broken)

## Estimated Complexity

| Task | Effort |
|------|--------|
| Initial setup (playwright.config.ts, fixtures, helpers, auth setup if needed) | 4-6 hours |
| Test fixture data setup (scan videos, create project via API before browser tests) | 1-2 hours |
| 9 E2E test specifications | 8-12 hours |
| CI integration (GitHub Actions job, artifact handling) | 2-3 hours |
| **Total** | **15-23 hours** |

The effort estimate assumes familiarity with Playwright. The `data-testid` attributes already present in the codebase significantly reduce the selector authoring effort.
