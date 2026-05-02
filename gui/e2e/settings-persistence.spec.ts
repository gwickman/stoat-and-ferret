import { test, expect } from "@playwright/test";

/**
 * J602: Settings Persistence (BL-297)
 *
 * Validates that theme selection and keyboard shortcut customizations persist
 * across page reloads via stoat-theme and stoat-shortcuts localStorage keys.
 */

test.describe("J602: theme persistence", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/gui/");
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await expect(page.getByTestId("workspace-layout")).toBeVisible();
  });

  test("clicking dark theme updates HTML data-theme attribute immediately", async ({
    page,
  }) => {
    await page.keyboard.press("Control+,");
    await expect(page.getByTestId("settings-panel")).toBeVisible();

    await page.getByTestId("theme-option-dark").click();

    const themeAttr = await page.evaluate(
      () => document.documentElement.dataset.theme,
    );
    expect(themeAttr).toBe("dark");
  });

  test("theme change writes to stoat-theme localStorage key", async ({
    page,
  }) => {
    await page.keyboard.press("Control+,");
    await expect(page.getByTestId("settings-panel")).toBeVisible();

    await page.getByTestId("theme-option-dark").click();

    const theme = await page.evaluate(() => {
      const raw = localStorage.getItem("stoat-theme");
      return raw ? JSON.parse(raw) : null;
    });
    expect(theme).toBe("dark");
  });

  test("theme persists after page reload (dark)", async ({ page }) => {
    await page.keyboard.press("Control+,");
    await expect(page.getByTestId("settings-panel")).toBeVisible();
    await page.getByTestId("theme-option-dark").click();
    await page.getByTestId("settings-panel-close").click();

    await page.reload();
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    const themeAttr = await page.evaluate(
      () => document.documentElement.dataset.theme,
    );
    expect(themeAttr).toBe("dark");

    const storedTheme = await page.evaluate(() => {
      const raw = localStorage.getItem("stoat-theme");
      return raw ? JSON.parse(raw) : null;
    });
    expect(storedTheme).toBe("dark");
  });

  test("theme persists after page reload (light)", async ({ page }) => {
    await page.keyboard.press("Control+,");
    await expect(page.getByTestId("settings-panel")).toBeVisible();
    await page.getByTestId("theme-option-light").click();
    await page.getByTestId("settings-panel-close").click();

    await page.reload();
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    const storedTheme = await page.evaluate(() => {
      const raw = localStorage.getItem("stoat-theme");
      return raw ? JSON.parse(raw) : null;
    });
    expect(storedTheme).toBe("light");
  });

  test("theme-option button reflects selected theme via aria-pressed", async ({
    page,
  }) => {
    await page.keyboard.press("Control+,");
    await expect(page.getByTestId("settings-panel")).toBeVisible();

    await page.getByTestId("theme-option-dark").click();

    await expect(page.getByTestId("theme-option-dark")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    await expect(page.getByTestId("theme-option-light")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });
});

test.describe("J602: keyboard shortcut persistence", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/gui/");
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await expect(page.getByTestId("workspace-layout")).toBeVisible();
  });

  test("shortcut rebind writes to stoat-shortcuts localStorage key", async ({
    page,
  }) => {
    await page.keyboard.press("Control+,");
    await expect(page.getByTestId("settings-panel")).toBeVisible();

    const inputSelector = '[data-testid="shortcut-input-workspace.preset.edit"]';
    await page.fill(inputSelector, "Ctrl+Shift+1");
    await page.getByTestId("shortcut-save-workspace.preset.edit").click();

    // Verify no error is shown
    await expect(
      page.getByTestId("shortcut-error-workspace.preset.edit"),
    ).not.toBeVisible();

    const shortcuts = await page.evaluate(() => {
      const raw = localStorage.getItem("stoat-shortcuts");
      return raw ? JSON.parse(raw) : null;
    });
    expect(shortcuts?.["workspace.preset.edit"]).toBe("Ctrl+Shift+1");
  });

  test("rebound shortcut restores from localStorage after page reload", async ({
    page,
  }) => {
    await page.keyboard.press("Control+,");
    await expect(page.getByTestId("settings-panel")).toBeVisible();

    await page.fill(
      '[data-testid="shortcut-input-workspace.preset.edit"]',
      "Ctrl+Shift+1",
    );
    await page.getByTestId("shortcut-save-workspace.preset.edit").click();
    await page.getByTestId("settings-panel-close").click();

    await page.reload();
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    // Open settings panel again to verify the input shows the saved shortcut.
    await page.keyboard.press("Control+,");
    await expect(page.getByTestId("settings-panel")).toBeVisible();

    const inputValue = await page
      .getByTestId("shortcut-input-workspace.preset.edit")
      .inputValue();
    expect(inputValue).toBe("Ctrl+Shift+1");
  });

  test("rebound shortcut activates preset after page reload", async ({
    page,
  }) => {
    await page.keyboard.press("Control+,");
    await expect(page.getByTestId("settings-panel")).toBeVisible();

    await page.fill(
      '[data-testid="shortcut-input-workspace.preset.edit"]',
      "Ctrl+Shift+1",
    );
    await page.getByTestId("shortcut-save-workspace.preset.edit").click();
    await page.getByTestId("settings-panel-close").click();

    await page.reload();
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    // Switch to a different preset first so there is a visible change.
    await page.selectOption(
      '[data-testid="workspace-preset-selector"]',
      "review",
    );
    await expect(
      page.getByTestId("workspace-preset-selector"),
    ).toHaveValue("review");

    // New shortcut should activate edit preset.
    await page.locator("body").click();
    await page.keyboard.press("Control+Shift+1");

    await expect(
      page.getByTestId("workspace-preset-selector"),
    ).toHaveValue("edit");
  });

  test("old shortcut no longer fires after rebind", async ({ page }) => {
    await page.keyboard.press("Control+,");
    await expect(page.getByTestId("settings-panel")).toBeVisible();

    await page.fill(
      '[data-testid="shortcut-input-workspace.preset.edit"]',
      "Ctrl+Shift+1",
    );
    await page.getByTestId("shortcut-save-workspace.preset.edit").click();
    await page.getByTestId("settings-panel-close").click();

    await page.reload();
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    // Start on review preset.
    await page.selectOption(
      '[data-testid="workspace-preset-selector"]',
      "review",
    );
    await expect(
      page.getByTestId("workspace-preset-selector"),
    ).toHaveValue("review");

    // Old shortcut Ctrl+1 should not switch to edit (binding is now Ctrl+Shift+1).
    await page.locator("body").click();
    await page.keyboard.press("Control+1");

    // Preset should stay on review.
    await expect(
      page.getByTestId("workspace-preset-selector"),
    ).toHaveValue("review");
  });

  test("reserved combo shows error and does not save", async ({ page }) => {
    await page.keyboard.press("Control+,");
    await expect(page.getByTestId("settings-panel")).toBeVisible();

    // Ctrl+R is browser-reserved — the store should reject it.
    await page.fill(
      '[data-testid="shortcut-input-workspace.preset.edit"]',
      "Ctrl+R",
    );
    await page.getByTestId("shortcut-save-workspace.preset.edit").click();

    await expect(
      page.getByTestId("shortcut-error-workspace.preset.edit"),
    ).toBeVisible();

    // localStorage should not be updated with the invalid combo.
    const shortcuts = await page.evaluate(() => {
      const raw = localStorage.getItem("stoat-shortcuts");
      return raw ? JSON.parse(raw) : null;
    });
    // Either not saved at all, or still the default value.
    if (shortcuts !== null) {
      expect(shortcuts["workspace.preset.edit"]).not.toBe("Ctrl+R");
    }
  });
});
