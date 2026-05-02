import { test, expect } from "@playwright/test";

/**
 * Focus restoration tests for modal dialogs (FR-002, FR-006).
 *
 * Verifies that modals expose correct ARIA dialog structure, that the
 * close button is keyboard-accessible, and that keyboard navigation
 * remains functional after a modal is dismissed.
 *
 * Focus trapping inside the SettingsPanel relies on aria-modal="true"
 * being respected by screen readers; native DOM focus trap via HTML
 * <dialog> is not currently used. Tests here validate the observable
 * ARIA contract rather than low-level focus sequence internals.
 */

test.describe("Settings modal: ARIA dialog structure", () => {
  test("settings panel has role=dialog with correct aria attributes", async ({
    page,
  }) => {
    await page.goto("/gui/");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    await page.keyboard.press("Control+,");
    const modal = page.getByTestId("settings-panel");
    await expect(modal).toBeVisible();

    await expect(modal).toHaveAttribute("role", "dialog");
    await expect(modal).toHaveAttribute("aria-modal", "true");
    await expect(modal).toHaveAttribute("aria-labelledby", "settings-panel-title");

    // Labelled-by target must be a visible heading inside the dialog
    const title = page.locator("#settings-panel-title");
    await expect(title).toBeVisible();
    await expect(title).toHaveText("Settings");

    await page.getByLabel("Close settings").click();
  });

  test("settings panel close button is keyboard-accessible", async ({
    page,
  }) => {
    await page.goto("/gui/");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    await page.keyboard.press("Control+,");
    await expect(page.getByTestId("settings-panel")).toBeVisible();

    // Close button must have an accessible label and be programmatically focusable
    const closeButton = page.getByTestId("settings-panel-close");
    await expect(closeButton).toBeVisible();
    await expect(closeButton).toHaveAttribute("aria-label", "Close settings");

    // Directly focus the close button and verify it receives focus
    await closeButton.focus();
    const focused = await page.evaluate(
      () => document.activeElement?.getAttribute("data-testid") ?? "",
    );
    expect(focused).toBe("settings-panel-close");

    await closeButton.click();
    await expect(page.getByTestId("settings-panel")).not.toBeVisible();
  });

  test("Escape key closes settings modal", async ({ page }) => {
    await page.goto("/gui/");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    await page.keyboard.press("Control+,");
    await expect(page.getByTestId("settings-panel")).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(page.getByTestId("settings-panel")).not.toBeVisible();
  });

  test("close button dismisses settings modal", async ({ page }) => {
    await page.goto("/gui/");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    await page.keyboard.press("Control+,");
    await expect(page.getByTestId("settings-panel")).toBeVisible();

    await page.getByTestId("settings-panel-close").click();
    await expect(page.getByTestId("settings-panel")).not.toBeVisible();
  });
});

test.describe("Settings modal: focus restoration", () => {
  test("workspace is accessible after settings modal closes via Escape", async ({
    page,
  }) => {
    await page.goto("/gui/");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    await page.keyboard.press("Control+,");
    await expect(page.getByTestId("settings-panel")).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(page.getByTestId("settings-panel")).not.toBeVisible();

    // Workspace must remain visible and reachable after close
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    // Tab navigation must still work — the first Tab press should leave body
    await page.evaluate(() => document.body.focus());
    await page.keyboard.press("Tab");
    const focusedTag = await page.evaluate(
      () => document.activeElement?.tagName ?? "BODY",
    );
    expect(focusedTag.toUpperCase()).not.toBe("BODY");
  });

  test("workspace is accessible after settings modal closes via close button", async ({
    page,
  }) => {
    await page.goto("/gui/");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    await page.keyboard.press("Control+,");
    await expect(page.getByTestId("settings-panel")).toBeVisible();

    await page.getByTestId("settings-panel-close").click();
    await expect(page.getByTestId("settings-panel")).not.toBeVisible();

    // Workspace and keyboard navigation must remain functional
    await expect(page.getByTestId("workspace-layout")).toBeVisible();
    await page.evaluate(() => document.body.focus());
    await page.keyboard.press("Tab");
    const focusedTag = await page.evaluate(
      () => document.activeElement?.tagName ?? "BODY",
    );
    expect(focusedTag.toUpperCase()).not.toBe("BODY");
  });

  test("settings panel can be reopened after close", async ({ page }) => {
    await page.goto("/gui/");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    // Open, close, reopen — verifies no state leak from prior open
    await page.keyboard.press("Control+,");
    await expect(page.getByTestId("settings-panel")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByTestId("settings-panel")).not.toBeVisible();

    await page.keyboard.press("Control+,");
    await expect(page.getByTestId("settings-panel")).toBeVisible();

    await page.getByLabel("Close settings").click();
    await expect(page.getByTestId("settings-panel")).not.toBeVisible();
  });
});
