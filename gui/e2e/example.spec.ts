import { test, expect } from "@playwright/test";

test("frontend loads from FastAPI", async ({ page }) => {
  await page.goto("/gui/");
  await expect(page).toHaveTitle("gui");
  // After BL-306, page content is panel-based. Verify the workspace shell loads.
  await expect(page.getByTestId("status-bar")).toBeVisible();
  await expect(page.getByTestId("workspace-layout")).toBeVisible();
});
