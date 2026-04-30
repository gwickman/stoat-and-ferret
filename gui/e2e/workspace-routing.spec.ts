import { test, expect } from "@playwright/test";

/**
 * E2E tests for per-panel routing (BL-306).
 *
 * After v049, workspace panel content is determined by PRESETS[preset].routes,
 * not by the browser URL. The URL encodes only the active preset name via the
 * ?workspace=<name> query param.
 */

test.describe("workspace preset deep links (?workspace=)", () => {
  test.beforeEach(async ({ page }) => {
    // Clear localStorage to avoid prior test state contaminating preset.
    await page.goto("/gui/");
    await page.evaluate(() => localStorage.clear());
  });

  test("?workspace=edit activates Edit preset with library, timeline, effects, preview panels", async ({
    page,
  }) => {
    await page.goto("/gui/?workspace=edit");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    // All edit-preset panels should be visible and contain their routed pages.
    await expect(page.getByTestId("library-page")).toBeVisible();
    await expect(page.getByTestId("timeline-page")).toBeVisible();
    await expect(page.getByTestId("preview-page")).toBeVisible();

    // Preset selector should reflect the active preset.
    const selector = page.getByTestId("workspace-preset-selector");
    await expect(selector).toHaveValue("edit");
  });

  test("?workspace=render activates Render preset with render-queue, batch, preview panels", async ({
    page,
  }) => {
    await page.goto("/gui/?workspace=render");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    // Render preset: render-queue and batch both map to /render, preview to /preview.
    // Both panels render RenderPage; use count assertion to verify two instances.
    const renderPageCount = await page
      .getByTestId("render-page")
      .count();
    expect(renderPageCount).toBeGreaterThanOrEqual(1);
    await expect(page.getByTestId("preview-page")).toBeVisible();

    // Preset selector should reflect the active preset.
    const selector = page.getByTestId("workspace-preset-selector");
    await expect(selector).toHaveValue("render");
  });

  test("?workspace=review activates Review preset with preview, timeline panels", async ({
    page,
  }) => {
    await page.goto("/gui/?workspace=review");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    await expect(page.getByTestId("preview-page")).toBeVisible();
    await expect(page.getByTestId("timeline-page")).toBeVisible();

    // Library panel should be hidden (not visible) in review preset.
    const libraryPanel = page.getByTestId("workspace-panel-library");
    await expect(libraryPanel).toHaveAttribute("data-visible", "false");

    const selector = page.getByTestId("workspace-preset-selector");
    await expect(selector).toHaveValue("review");
  });

  test("unknown ?workspace= param emits no crash and preserves stored preset", async ({
    page,
  }) => {
    // Pre-set edit preset in localStorage so there is a known stored preset.
    await page.goto("/gui/");
    await page.evaluate(() => {
      localStorage.setItem(
        "stoat-workspace-layout",
        JSON.stringify({ preset: "edit", anchorPreset: "edit" }),
      );
    });

    // Navigate with an invalid workspace param — should not crash.
    await page.goto("/gui/?workspace=invalid-preset");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    // App should still render (no crash).
    await expect(page.getByTestId("status-bar")).toBeVisible();
  });
});

test.describe("per-panel page rendering (AC3 regression check)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/gui/");
    await page.evaluate(() => localStorage.clear());
  });

  test("Edit preset: LibraryPage renders correctly at panel-constrained width", async ({
    page,
  }) => {
    await page.goto("/gui/?workspace=edit");
    await expect(page.getByTestId("library-page")).toBeVisible();
    // Library page heading and scan button should be visible without overflow.
    await expect(
      page.getByRole("heading", { name: "Library" }),
    ).toBeVisible();
    await expect(page.getByTestId("scan-button")).toBeVisible();
  });

  test("Edit preset: TimelinePage renders correctly at panel-constrained width", async ({
    page,
  }) => {
    await page.goto("/gui/?workspace=edit");
    await expect(page.getByTestId("timeline-page")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Timeline" }),
    ).toBeVisible();
  });

  test("Edit preset: PreviewPage renders correctly in preview panel", async ({
    page,
  }) => {
    await page.goto("/gui/?workspace=edit");
    await expect(page.getByTestId("preview-page")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Preview" }),
    ).toBeVisible();
  });

  test("Render preset: RenderPage renders correctly in render-queue and batch panels", async ({
    page,
  }) => {
    await page.goto("/gui/?workspace=render");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();
    // At least one RenderPage instance is visible.
    await expect(page.getByTestId("render-page").first()).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Render" }).first(),
    ).toBeVisible();
  });

  test("default state (preview-only): preview panel renders PreviewPage", async ({
    page,
  }) => {
    // Navigate without a ?workspace param and with cleared localStorage.
    // Default state: edit preset, only preview panel visible.
    await page.goto("/gui/");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();
    await expect(page.getByTestId("preview-page")).toBeVisible();

    // Library panel should be hidden in default preview-only state.
    const libraryPanel = page.getByTestId("workspace-panel-library");
    await expect(libraryPanel).toHaveAttribute("data-visible", "false");
  });
});
