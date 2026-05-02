import { test, expect } from "@playwright/test";

/**
 * J601: Workspace Layout Persistence (BL-297)
 *
 * Validates that workspace presets and panel sizes persist across page reloads
 * via the stoat-workspace-layout localStorage key. Tests the full
 * Zustand → localStorage → reload → restore round-trip.
 */

test.describe("J601: workspace layout localStorage persistence", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/gui/");
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await expect(page.getByTestId("workspace-layout")).toBeVisible();
  });

  test("preset selector change writes stoat-workspace-layout immediately", async ({
    page,
  }) => {
    await page.selectOption(
      '[data-testid="workspace-preset-selector"]',
      "review",
    );

    const stored = await page.evaluate(() => {
      const raw = localStorage.getItem("stoat-workspace-layout");
      return raw ? JSON.parse(raw) : null;
    });

    expect(stored).not.toBeNull();
    expect(stored.preset).toBe("review");
  });

  test("stoat-workspace-layout JSON has required shape keys", async ({
    page,
  }) => {
    await page.selectOption(
      '[data-testid="workspace-preset-selector"]',
      "edit",
    );

    const stored = await page.evaluate(() => {
      const raw = localStorage.getItem("stoat-workspace-layout");
      return raw ? JSON.parse(raw) : null;
    });

    expect(stored).toHaveProperty("preset");
    expect(stored).toHaveProperty("anchorPreset");
    expect(stored).toHaveProperty("panelSizes");
    expect(stored).toHaveProperty("panelVisibility");
    expect(stored).toHaveProperty("sizesByPreset");
  });

  test("edit preset sizes stored correctly in panelSizes", async ({ page }) => {
    await page.selectOption(
      '[data-testid="workspace-preset-selector"]',
      "edit",
    );

    const panelSizes = await page.evaluate(() => {
      const raw = localStorage.getItem("stoat-workspace-layout");
      return raw ? JSON.parse(raw).panelSizes : null;
    });

    expect(panelSizes).not.toBeNull();
    expect(panelSizes.library).toBe(20);
    expect(panelSizes.timeline).toBe(35);
    expect(panelSizes.effects).toBe(15);
    expect(panelSizes.preview).toBe(30);
  });

  test("review preset sizes stored correctly in panelSizes", async ({
    page,
  }) => {
    await page.selectOption(
      '[data-testid="workspace-preset-selector"]',
      "review",
    );

    const panelSizes = await page.evaluate(() => {
      const raw = localStorage.getItem("stoat-workspace-layout");
      return raw ? JSON.parse(raw).panelSizes : null;
    });

    expect(panelSizes).not.toBeNull();
    expect(panelSizes.preview).toBe(60);
    expect(panelSizes.timeline).toBe(40);
  });

  test("preset restores from localStorage after page reload (review)", async ({
    page,
  }) => {
    await page.selectOption(
      '[data-testid="workspace-preset-selector"]',
      "review",
    );
    await expect(
      page.getByTestId("workspace-preset-selector"),
    ).toHaveValue("review");

    await page.reload();
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    await expect(
      page.getByTestId("workspace-preset-selector"),
    ).toHaveValue("review");
  });

  test("preset restores from localStorage after page reload (render)", async ({
    page,
  }) => {
    await page.selectOption(
      '[data-testid="workspace-preset-selector"]',
      "render",
    );

    await page.reload();
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    await expect(
      page.getByTestId("workspace-preset-selector"),
    ).toHaveValue("render");
  });

  test("custom panel size persists in sizesByPreset across reload", async ({
    page,
  }) => {
    // Simulate a panel resize by writing directly to localStorage (mirroring
    // what workspaceStore.resizePanel would produce).
    await page.evaluate(() => {
      localStorage.setItem(
        "stoat-workspace-layout",
        JSON.stringify({
          preset: "custom",
          anchorPreset: "edit",
          panelSizes: {
            library: 20,
            timeline: 35,
            effects: 25,
            preview: 30,
            "render-queue": 0,
            batch: 0,
          },
          panelVisibility: {
            library: true,
            timeline: true,
            effects: true,
            preview: true,
            "render-queue": false,
            batch: false,
          },
          sizesByPreset: { edit: { effects: 25 } },
        }),
      );
    });
    await page.reload();
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    const stored = await page.evaluate(() => {
      const raw = localStorage.getItem("stoat-workspace-layout");
      return raw ? JSON.parse(raw) : null;
    });

    expect(stored.preset).toBe("custom");
    expect(stored.sizesByPreset?.edit?.effects).toBe(25);

    await expect(
      page.getByTestId("workspace-preset-selector"),
    ).toHaveValue("custom");
  });
});

test.describe("J601: preset switch via keyboard shortcuts", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/gui/");
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await expect(page.getByTestId("workspace-layout")).toBeVisible();
  });

  test("Ctrl+2 switches to review preset and persists to localStorage", async ({
    page,
  }) => {
    // Click workspace layout so focus is off any form control.
    await page.locator("body").click();
    await page.keyboard.press("Control+2");

    await expect(
      page.getByTestId("workspace-preset-selector"),
    ).toHaveValue("review");

    const preset = await page.evaluate(() => {
      const raw = localStorage.getItem("stoat-workspace-layout");
      return raw ? JSON.parse(raw).preset : null;
    });
    expect(preset).toBe("review");
  });

  test("Ctrl+3 switches to render preset and persists to localStorage", async ({
    page,
  }) => {
    await page.locator("body").click();
    await page.keyboard.press("Control+3");

    await expect(
      page.getByTestId("workspace-preset-selector"),
    ).toHaveValue("render");

    const preset = await page.evaluate(() => {
      const raw = localStorage.getItem("stoat-workspace-layout");
      return raw ? JSON.parse(raw).preset : null;
    });
    expect(preset).toBe("render");
  });

  test("Ctrl+1 switches to edit preset and persists to localStorage", async ({
    page,
  }) => {
    // Start on review so there is a visible change.
    await page.selectOption(
      '[data-testid="workspace-preset-selector"]',
      "review",
    );
    await expect(
      page.getByTestId("workspace-preset-selector"),
    ).toHaveValue("review");

    await page.locator("body").click();
    await page.keyboard.press("Control+1");

    await expect(
      page.getByTestId("workspace-preset-selector"),
    ).toHaveValue("edit");

    const preset = await page.evaluate(() => {
      const raw = localStorage.getItem("stoat-workspace-layout");
      return raw ? JSON.parse(raw).preset : null;
    });
    expect(preset).toBe("edit");
  });

  test("keyboard preset switch persists after page reload", async ({ page }) => {
    await page.locator("body").click();
    await page.keyboard.press("Control+2");
    await expect(
      page.getByTestId("workspace-preset-selector"),
    ).toHaveValue("review");

    await page.reload();
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    await expect(
      page.getByTestId("workspace-preset-selector"),
    ).toHaveValue("review");
  });
});
