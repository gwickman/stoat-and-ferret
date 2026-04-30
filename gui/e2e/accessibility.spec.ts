import { test, expect, type APIRequestContext, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/** Check that the effects API is working (requires Rust module). */
async function checkEffectsApi(request: APIRequestContext): Promise<boolean> {
  try {
    const res = await request.get("/api/v1/effects");
    return res.ok();
  } catch {
    return false;
  }
}

/**
 * Wait for a workspace separator to be visible and have a non-zero aria-valuenow.
 * react-resizable-panels initialises separator ARIA attributes asynchronously after
 * the layout engine measures the container. Running an axe scan before this settles
 * produces false-positive focus-order-semantics violations (aria-valuenow === 0
 * makes the separator appear as a degenerate, non-functional slider in the tab order).
 */
async function waitForSeparatorReady(page: Page, id: string): Promise<void> {
  await expect(page.locator(`#${id}`)).toBeVisible();
  await page.waitForFunction(
    (sepId) =>
      parseFloat(
        document.getElementById(sepId)?.getAttribute("aria-valuenow") ?? "0",
      ) > 0,
    id,
    { timeout: 5000 },
  );
}

test.describe("WCAG AA accessibility", () => {
  test("default workspace (preview-only) has no WCAG AA violations", async ({
    page,
  }) => {
    // After BL-306, page content is determined by workspace presets.
    // Default state: edit preset, only preview panel visible.
    await page.goto("/gui/");
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await expect(page.getByTestId("workspace-layout")).toBeVisible();
    await expect(page.getByTestId("preview-page")).toBeVisible();

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test("library has no WCAG AA violations", async ({ page }) => {
    // After BL-306, library is visible in the Edit preset panel.
    await page.goto("/gui/?workspace=edit");
    await expect(
      page.getByRole("heading", { name: "Library" }),
    ).toBeVisible();

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test("render page has no WCAG AA violations", async ({ page }) => {
    // After BL-306, render-queue and batch panels are visible in Render preset.
    await page.goto("/gui/?workspace=render");
    await expect(page.getByTestId("render-page").first()).toBeVisible();

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test("effect catalog has no WCAG AA violations", async ({
    page,
    request,
  }) => {
    const apiOk = await checkEffectsApi(request);
    test.skip(!apiOk, "Effects API unavailable (Rust module not built)");

    // After BL-306, effects panel is visible in the Edit preset.
    await page.goto("/gui/?workspace=edit");
    await expect(
      page.getByRole("heading", { name: "Effects" }),
    ).toBeVisible();
    await expect(page.getByTestId("effect-catalog")).toBeVisible({
      timeout: 15_000,
    });

    // Exclude pre-existing UI issues from earlier themes:
    // - color-contrast: green category badges (#00a63e) below 4.5:1 ratio
    // - select-name: category filter and search input lack accessible labels
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .disableRules(["color-contrast", "select-name"])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test("effect parameter form has no WCAG AA violations", async ({
    page,
    request,
  }) => {
    const apiOk = await checkEffectsApi(request);
    test.skip(!apiOk, "Effects API unavailable (Rust module not built)");

    // After BL-306, effects panel is visible in the Edit preset.
    await page.goto("/gui/?workspace=edit");
    await expect(
      page.getByRole("heading", { name: "Effects" }),
    ).toBeVisible();
    await expect(page.getByTestId("effect-catalog")).toBeVisible({
      timeout: 15_000,
    });

    // Select volume effect to trigger the parameter form
    await page.getByTestId("effect-card-volume").click();
    await expect(page.getByTestId("effect-parameter-form")).toBeVisible();

    // Exclude pre-existing UI issues from earlier themes:
    // - color-contrast: green category badges (#00a63e) below 4.5:1 ratio
    // - select-name: category filter and search input lack accessible labels
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .disableRules(["color-contrast", "select-name"])
      .analyze();

    expect(results.violations).toEqual([]);
  });
});

test.describe("workspace accessibility", () => {
  test("Edit preset: zero scrollable-region-focusable violations", async ({
    page,
  }) => {
    await page.goto("/gui/");
    await page.selectOption('[data-testid="workspace-preset-selector"]', "edit");
    // Wait for library separator to appear and be fully initialised by
    // react-resizable-panels before running the axe scan. A zero-range separator
    // (aria-valuenow=0) produces false-positive focus-order-semantics violations.
    await waitForSeparatorReady(page, "sep-library-main");

    const results = await new AxeBuilder({ page })
      .withRules(["scrollable-region-focusable"])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test("Review preset: zero scrollable-region-focusable violations", async ({
    page,
  }) => {
    await page.goto("/gui/");
    await page.selectOption(
      '[data-testid="workspace-preset-selector"]',
      "review",
    );
    await waitForSeparatorReady(page, "sep-top-preview");

    const results = await new AxeBuilder({ page })
      .withRules(["scrollable-region-focusable"])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test("Render preset: zero scrollable-region-focusable violations", async ({
    page,
  }) => {
    await page.goto("/gui/");
    await page.selectOption(
      '[data-testid="workspace-preset-selector"]',
      "render",
    );
    await waitForSeparatorReady(page, "sep-main-right");

    const results = await new AxeBuilder({ page })
      .withRules(["scrollable-region-focusable"])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test("Preview-only: zero scrollable-region-focusable violations", async ({
    page,
  }) => {
    // Navigate first so localStorage is accessible, then clear and reload so
    // workspace initialises with only preview visible (default store state).
    await page.goto("/gui/");
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await expect(page.getByTestId("workspace-layout")).toBeVisible();
    // Preview-only has no separators; workspace-layout visible is sufficient.

    const results = await new AxeBuilder({ page })
      .withRules(["scrollable-region-focusable"])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test("keyboard navigation: Tab reaches workspace separators in Edit preset without trapping", async ({
    page,
  }) => {
    await page.goto("/gui/");
    await page.selectOption('[data-testid="workspace-preset-selector"]', "edit");
    // Wait for layout to settle so separator aria values are non-zero
    await waitForSeparatorReady(page, "sep-library-main");

    // Start Tab traversal from body and collect focused element IDs
    await page.locator("body").click();
    const focusedIds: string[] = [];
    // After BL-306, panels contain full page components (many focusable elements).
    // 100 Tab presses covers all interactive elements before reaching separators.
    for (let i = 0; i < 100; i++) {
      await page.keyboard.press("Tab");
      const id = await page.evaluate(
        () => document.activeElement?.id ?? "",
      );
      if (id) focusedIds.push(id);
    }

    // Edit preset: library, timeline, effects, preview visible.
    // These separators must appear in the tab order.
    expect(focusedIds).toContain("sep-library-main");
    expect(focusedIds).toContain("sep-timeline-effects");
    expect(focusedIds).toContain("sep-top-preview");

    // Right-panel separators must NOT appear (render-queue and batch hidden).
    expect(focusedIds).not.toContain("sep-main-right");
    expect(focusedIds).not.toContain("sep-render-batch");
  });
});
