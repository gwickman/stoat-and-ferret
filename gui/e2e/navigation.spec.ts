import { test, expect } from "@playwright/test";

test.describe("Navigation", () => {
  test("navigates between tabs and updates URL", async ({ page }) => {
    // Start with edit preset so all panels are visible and pages render.
    await page.goto("/gui/?workspace=edit");
    await expect(page.getByTestId("workspace-layout")).toBeVisible();

    // Library panel is visible with LibraryPage in edit preset.
    await expect(page.getByTestId("library-page")).toBeVisible();

    // Click Library nav tab — URL should update.
    await page.getByTestId("nav-tab-library").click();
    await expect(page).toHaveURL(/\/gui\/library/);

    // Click Projects nav tab — URL should update.
    await page.getByTestId("nav-tab-projects").click();
    await expect(page).toHaveURL(/\/gui\/projects/);

    // Click Dashboard nav tab — URL should update.
    await page.getByTestId("nav-tab-dashboard").click();
    await expect(page).toHaveURL(/\/gui\/?$/);
  });
});
