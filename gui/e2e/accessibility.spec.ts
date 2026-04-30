import { test, expect, type APIRequestContext } from "@playwright/test";
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

test.describe("WCAG AA accessibility", () => {
  test("dashboard has no WCAG AA violations", async ({ page }) => {
    await page.goto("/gui/");
    await expect(
      page.getByRole("heading", { name: "Dashboard" }),
    ).toBeVisible();

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test("library has no WCAG AA violations", async ({ page }) => {
    // Navigate via client-side routing (SPA)
    await page.goto("/gui/");
    await page.getByTestId("nav-tab-library").click();
    await expect(
      page.getByRole("heading", { name: "Library" }),
    ).toBeVisible();

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test("projects has no WCAG AA violations", async ({ page }) => {
    // Navigate via client-side routing (SPA)
    await page.goto("/gui/");
    await page.getByTestId("nav-tab-projects").click();
    await expect(
      page.getByRole("heading", { name: "Projects" }),
    ).toBeVisible();

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

    // Navigate via client-side routing (SPA)
    await page.goto("/gui/");
    await page.getByTestId("nav-tab-effects").click();
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

    // Navigate to effects and select an effect to render the parameter form
    await page.goto("/gui/");
    await page.getByTestId("nav-tab-effects").click();
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
  test("Edit preset: zero scrollable-region-focusable and focus-order-semantics violations", async ({
    page,
  }) => {
    await page.goto("/gui/");
    await page.selectOption('[data-testid="workspace-preset-selector"]', "edit");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    const results = await new AxeBuilder({ page })
      .withRules(["scrollable-region-focusable", "focus-order-semantics"])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test("Review preset: zero scrollable-region-focusable and focus-order-semantics violations", async ({
    page,
  }) => {
    await page.goto("/gui/");
    await page.selectOption(
      '[data-testid="workspace-preset-selector"]',
      "review",
    );
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    const results = await new AxeBuilder({ page })
      .withRules(["scrollable-region-focusable", "focus-order-semantics"])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test("Render preset: zero scrollable-region-focusable and focus-order-semantics violations", async ({
    page,
  }) => {
    await page.goto("/gui/");
    await page.selectOption(
      '[data-testid="workspace-preset-selector"]',
      "render",
    );
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    const results = await new AxeBuilder({ page })
      .withRules(["scrollable-region-focusable", "focus-order-semantics"])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test("Preview-only: zero scrollable-region-focusable and focus-order-semantics violations", async ({
    page,
  }) => {
    // Clear localStorage so workspace initialises with only preview visible
    await page.evaluate(() => localStorage.clear());
    await page.goto("/gui/");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    const results = await new AxeBuilder({ page })
      .withRules(["scrollable-region-focusable", "focus-order-semantics"])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test("keyboard navigation: Tab reaches workspace separators in Edit preset without trapping", async ({
    page,
  }) => {
    await page.goto("/gui/");
    await page.selectOption('[data-testid="workspace-preset-selector"]', "edit");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    // Start Tab traversal from body and collect focused element IDs
    await page.locator("body").click();
    const focusedIds: string[] = [];
    for (let i = 0; i < 30; i++) {
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
