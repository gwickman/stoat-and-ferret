import { test, expect } from "@playwright/test";

test("frontend loads from FastAPI", async ({ page }) => {
  await page.goto("/gui/");
  await expect(page).toHaveTitle("gui");
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
});
