# Browser Compatibility Baseline

Established: 2026-05-02 (v054 / BL-299)

## Summary

J601–J606 journeys were executed on Chromium, Firefox 146, and WebKit 26 (Safari engine).
Chromium passes all journeys. Firefox passes all except J604 (focus trap detection). WebKit passes all except J602 (URL routing) and J604/J605 (skip-link focus). All failures are documented as known issues below.

## Test Matrix

| Journey | Spec File | Chromium | Firefox | WebKit |
|---------|-----------|----------|---------|--------|
| J601: workspace layout | workspace-layout.spec.ts | PASS | PASS | PASS |
| J602: URL routing | workspace-routing.spec.ts | PASS | PASS | FAIL (3) |
| J603: batch WebSocket | batch-panel.spec.ts | PASS | PASS | PASS |
| J604: keyboard navigation | keyboard-navigation.spec.ts | PASS | FAIL (4) | FAIL (4) |
| J605: accessibility | accessibility.spec.ts | PASS | PASS | FAIL (2) |
| J606: settings persistence | settings-persistence.spec.ts | PASS | PASS | PASS |

**Pass rates:**
- Chromium: 95/96 (1 skipped — effect-workshop test; pre-existing)
- Firefox: 91/96 (4 failed, 1 skipped)
- WebKit: 88/96 (7 failed, 1 skipped)

## Known Issues

### FF-001: Firefox focus trap detection — J604 (4 tests)

**Browser:** Firefox 146  
**Tests:**
- `keyboard-navigation.spec.ts:149` — Edit preset: no focus trap
- `keyboard-navigation.spec.ts:195` — Render preset: no focus trap
- `keyboard-navigation.spec.ts:238` — Review preset: no focus trap
- `accessibility.spec.ts:395` — Tab reaches workspace separators in Edit preset without trapping

**Symptom:** `trapDetected` is `true` in Firefox when the test expects `false`. The focus trap heuristic cycles Tab through interactive elements; Firefox counts cycles differently than Chromium/WebKit.

**Root cause:** Firefox's Tab-navigation cycle order for panel resize handles (`sep-*` elements) differs from Chromium. The test's loop cap is hit before Firefox cycles through all elements, triggering false-positive trap detection.

**Impact:** UI behavior is functionally correct — users can Tab through the workspace in Firefox. The test heuristic is Chromium-tuned and needs Firefox-aware handling.

**Product request:** Filed as PR candidate (see completion report).

---

### WK-001: WebKit skip-link focus — J604/J605 (4 tests)

**Browser:** WebKit 26 (Safari engine)  
**Tests:**
- `keyboard-navigation.spec.ts:12` — Tab from page load focuses skip-link as first stop
- `keyboard-navigation.spec.ts:27` — skip-link activation moves focus to #main-content
- `accessibility.spec.ts:195` — skip-link receives focus on first Tab press
- `accessibility.spec.ts:209` — activating skip-link moves focus to #main-content

**Symptom:** Skip-link focus assertions fail in WebKit.

**Root cause:** WebKit/Safari does not move keyboard focus to elements via programmatic `focus()` calls unless initiated by a direct user gesture. The `page.keyboard.press("Tab")` action in Playwright's WebKit implementation does not land on the skip-link as the first focusable element. This is a known Safari accessibility behavior difference.

**Impact:** Safari users using keyboard navigation may not get the skip-link as the first Tab stop. The skip-link HTML is present in the DOM and the link is valid; focus delivery is the WebKit-specific gap.

**Product request:** Filed as PR candidate (see completion report).

---

### WK-002: WebKit URL workspace parameter routing — J602 (3 tests)

**Browser:** WebKit 26 (Safari engine)  
**Tests:**
- `workspace-routing.spec.ts:19` — `?workspace=edit` activates Edit preset
- `workspace-routing.spec.ts:35` — `?workspace=render` activates Render preset
- `workspace-routing.spec.ts:54` — `?workspace=review` activates Review preset

**Symptom:** Workspace preset selector does not reflect the value set by the `?workspace=` URL parameter in WebKit. Received value is `"custom"` instead of the expected preset name.

**Root cause:** WebKit URL parameter parsing timing is slightly different from Chromium. The `zustand` state update from the URL parameter may not be applied before the test assertion fires, or WebKit's history/navigation handling triggers a different code path.

**Impact:** Deep-linking to a workspace preset via URL (`?workspace=render`) may not work reliably in Safari. Once the page loads and the user interacts with the preset selector, behavior is normal.

**Product request:** Filed as PR candidate (see completion report).

---

## CI Integration

CI runs **Chromium only** via the `!process.env.CI` guard in `gui/playwright.config.ts`.

GitHub Actions sets `CI=true` automatically on all job runs, which excludes the `firefox` and `webkit` projects from the `projects` array at parse time. The `e2e` CI job runs the same 96 tests on Chromium only; adding Firefox/WebKit to CI would require browser binaries and is a deliberate local-only workflow.

Multi-browser testing is a **local developer workflow**:

```bash
# Install browser binaries (one-time)
cd gui
npx playwright install chromium firefox webkit

# Run all three browsers
STOAT_TESTING_MODE=true npx playwright test

# Run a single browser
STOAT_TESTING_MODE=true npx playwright test --project=firefox
```

> **Note:** `STOAT_TESTING_MODE=true` is required to enable the seed endpoint tests (J606). CI sets this via the workflow environment. For local multi-browser runs, prefix the command or set the variable in your shell.

## Environment Notes

- **Chromium:** No known quirks. Baseline browser for CI.
- **Firefox 146:** Tab navigation cycle order differs from Chromium for panel resize handles. Skip-link and routing behavior is correct.
- **WebKit 26 (Safari engine):** Two distinct compatibility gaps: skip-link programmatic focus and URL parameter routing timing. WebKit also has intermittent server connectivity issues on Windows where `fullyParallel: true` causes some tests to start before the server is ready; run with `--workers=1` if this occurs.
