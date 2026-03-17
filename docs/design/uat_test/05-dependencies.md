# 05 — Dependencies

## New Dependencies

### playwright (pip package)

**Package:** `playwright` — Python bindings for the Playwright browser automation library.

**Why Python Playwright, not the existing TypeScript Playwright?**

The project already has Playwright installed in `gui/` for TypeScript E2E tests (`gui/e2e/`). However, the UAT script uses the Python Playwright package for these reasons:

1. **Python-first project.** The backend, smoke tests, test factories, seed script, and CI orchestration are all Python. A Python UAT script can reuse `httpx` for health-check polling, share the `seed_sample_project.py` logic, and import project constants directly.

2. **Structured bug reports.** The issue recording format (JSON + markdown with screenshots, console errors, API response logs) is straightforward to build in Python with full control over the test harness. A TypeScript implementation would require writing a custom Playwright reporter.

3. **Dual-mode support.** The same Python script supports `--headless` (automated Tier 1) and `--headed` (manual Tier 2) with a single codebase. No separate configuration or runner needed.

4. **Separation of concerns.** The TypeScript E2E tests in `gui/e2e/` are lightweight component-level checks. The UAT script is a different thing — a multi-journey acceptance test with evidence collection. Keeping them separate avoids conflating two testing concerns.

5. **Async patterns.** Python Playwright's `async/await` API matches the project's existing async patterns used throughout the codebase.

### Chromium Browser Binary

**Command:** `playwright install chromium`

**Size:** ~400MB download, cached after first install.

**Shared with TypeScript Playwright:** The Chromium binary installed by Python Playwright is the same browser binary used by TypeScript Playwright. Playwright stores browser binaries in a shared cache directory (`~/.cache/ms-playwright/` on Linux, platform-specific elsewhere), so both Python and TypeScript Playwright share the same downloaded browser.

## Dependencies NOT Added

| Dependency | Why Not |
|------------|---------|
| Selenium | No auto-wait (flaky in SPAs), no network interception, no trace files, slower WebDriver protocol, ChromeDriver version management burden |
| Cypress | Not Python-compatible, would add a third test framework alongside existing Playwright |
| Puppeteer | Node-only, no Python bindings, duplicates Playwright's CDP connection approach |
| pytest-playwright | Adds pytest runner overhead when the UAT script manages its own lifecycle; the script is not a test suite but an evidence-collecting runner |

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Two Playwright installations (Python + TypeScript) | Browser binaries are shared; only the Python bindings are new (~5MB pip package) |
| Headless screenshots miss visual bugs | Tier 2 headed mode for human verification when Tier 1 flags issues |
| Test flakiness from async rendering | Playwright's built-in auto-wait + explicit `page.wait_for_selector()` on `data-testid` attributes already used in existing E2E specs |
| Build/boot takes too long for CI | `--skip-build` flag; separate CI step for build, UAT step only runs journeys |
| Browser not available in exploration context | Headless mode works without display server; limitation documented |
| ~400MB Chromium download in CI | Cached between CI runs; one-time cost per CI runner |

## Installation

Add to project dependencies (in `pyproject.toml` under optional test dependencies):

```toml
[project.optional-dependencies]
uat = ["playwright>=1.40"]
```

Setup after installation:

```bash
pip install -e ".[uat]"
playwright install chromium
```
