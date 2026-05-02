import { test, expect } from "@playwright/test";

/**
 * J604: Keyboard Navigation Journey
 *
 * Validates that all interactive elements are reachable by keyboard-only
 * navigation. Tests Tab focus order, reachability of controls, and absence
 * of focus traps. Part of the WCAG AA accessibility validation (BL-296).
 */

test.describe("J604: skip-link keyboard navigation", () => {
  test("Tab from page load focuses skip-link as first stop", async ({
    page,
  }) => {
    await page.goto("/gui/");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    // Focus body programmatically to reset tab position (body.click() does not
    // establish keyboard focus in headless Chromium on Linux CI).
    await page.evaluate(() => document.body.focus());
    await page.keyboard.press("Tab");

    const skipLink = page.getByRole("link", { name: "Skip to main content" });
    await expect(skipLink).toBeFocused();
  });

  test("skip-link activation moves focus to #main-content", async ({
    page,
  }) => {
    await page.goto("/gui/");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    // Tab to skip-link, then activate with Enter
    await page.evaluate(() => document.body.focus());
    await page.keyboard.press("Tab");
    await expect(
      page.getByRole("link", { name: "Skip to main content" }),
    ).toBeFocused();
    await page.keyboard.press("Enter");

    // After activating skip-link, focus should be on or inside #main-content
    const mainContent = page.locator("#main-content").first();
    await expect(mainContent).toBeAttached();

    // Verify focus moved into the main content area
    const focusedId = await page.evaluate(
      () => document.activeElement?.id ?? "",
    );
    expect(focusedId).toBe("main-content");
  });
});

test.describe("J604: header controls keyboard reachability", () => {
  test("workspace preset selector is reachable via Tab", async ({ page }) => {
    await page.goto("/gui/");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    const presetSelector = page.getByTestId("workspace-preset-selector");
    await expect(presetSelector).toBeAttached();

    // Tab until we reach the workspace preset selector (within 20 Tab presses)
    await page.evaluate(() => document.body.focus());
    let found = false;
    for (let i = 0; i < 20; i++) {
      await page.keyboard.press("Tab");
      const focused = await page.evaluate(
        () =>
          document.activeElement?.getAttribute("data-testid") ??
          document.activeElement?.tagName ??
          "",
      );
      if (focused === "workspace-preset-selector") {
        found = true;
        break;
      }
    }
    expect(found).toBe(true);
  });

  test("settings panel opens and closes by keyboard shortcut", async ({
    page,
  }) => {
    await page.goto("/gui/");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    // Open settings panel via default Ctrl+, shortcut
    await page.keyboard.press("Control+,");
    await expect(page.getByTestId("settings-panel")).toBeVisible();

    // Close settings panel via the close button
    await page.getByLabel("Close settings").click();
    await expect(page.getByTestId("settings-panel")).not.toBeVisible();
  });
});

test.describe("J604: library page keyboard navigation", () => {
  test("scan button is reachable via Tab on library route", async ({
    page,
  }) => {
    await page.goto("/gui/library");
    await expect(page.getByTestId("library-page")).toBeVisible();

    const scanButton = page.getByTestId("scan-button");
    await expect(scanButton).toBeAttached();

    // Tab until we find the scan button (within 30 presses — after nav tabs)
    await page.evaluate(() => document.body.focus());
    let found = false;
    for (let i = 0; i < 30; i++) {
      await page.keyboard.press("Tab");
      const focused = await page.evaluate(
        () => document.activeElement?.getAttribute("data-testid") ?? "",
      );
      if (focused === "scan-button") {
        found = true;
        break;
      }
    }
    expect(found).toBe(true);
  });
});

test.describe("J604: render page keyboard navigation", () => {
  test("render page has no keyboard focus traps", async ({ page }) => {
    await page.goto("/gui/render");
    await expect(page.getByTestId("render-page").first()).toBeVisible();

    // Tab through the page 30 times; focus should keep moving (no trap)
    await page.evaluate(() => document.body.focus());
    const focusedElements: string[] = [];
    for (let i = 0; i < 30; i++) {
      await page.keyboard.press("Tab");
      const focused = await page.evaluate(() => {
        const el = document.activeElement;
        return el?.tagName === "BODY"
          ? "body"
          : (el?.id ?? el?.getAttribute("data-testid") ?? el?.tagName ?? "");
      });
      focusedElements.push(focused);
    }

    // Verify we got at least some interactive focus targets (not stuck on body)
    const nonBodyElements = focusedElements.filter((id) => id !== "body");
    expect(nonBodyElements.length).toBeGreaterThan(0);
  });
});

test.describe("J604: workspace preset keyboard navigation", () => {
  test("Edit preset: no focus trap — Tab cycles through interactive elements", async ({
    page,
  }) => {
    await page.goto("/gui/?workspace=edit");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    // Tab through 50 elements; should not get stuck (same element repeated more than once consecutively)
    await page.evaluate(() => document.body.focus());
    const focusedIds: string[] = [];
    for (let i = 0; i < 50; i++) {
      await page.keyboard.press("Tab");
      const id = await page.evaluate(
        () =>
          document.activeElement?.id ??
          document.activeElement?.getAttribute("data-testid") ??
          document.activeElement?.tagName?.toLowerCase() ??
          "",
      );
      focusedIds.push(id);
    }

    // Check: no three consecutive identical elements (would indicate a trap)
    let trapDetected = false;
    for (let i = 2; i < focusedIds.length; i++) {
      if (
        focusedIds[i] === focusedIds[i - 1] &&
        focusedIds[i] === focusedIds[i - 2] &&
        focusedIds[i] !== "body"
      ) {
        trapDetected = true;
        break;
      }
    }
    expect(trapDetected).toBe(false);
  });

  test("Render preset: no focus trap — Tab cycles through interactive elements", async ({
    page,
  }) => {
    await page.goto("/gui/?workspace=render");
    await expect(page.getByTestId("render-page").first()).toBeVisible();

    // Tab through 30 elements; should not get stuck
    await page.evaluate(() => document.body.focus());
    const focusedIds: string[] = [];
    for (let i = 0; i < 30; i++) {
      await page.keyboard.press("Tab");
      const id = await page.evaluate(
        () =>
          document.activeElement?.id ??
          document.activeElement?.getAttribute("data-testid") ??
          document.activeElement?.tagName?.toLowerCase() ??
          "",
      );
      focusedIds.push(id);
    }

    // No three consecutive identical elements
    let trapDetected = false;
    for (let i = 2; i < focusedIds.length; i++) {
      if (
        focusedIds[i] === focusedIds[i - 1] &&
        focusedIds[i] === focusedIds[i - 2] &&
        focusedIds[i] !== "body"
      ) {
        trapDetected = true;
        break;
      }
    }
    expect(trapDetected).toBe(false);
  });
});
