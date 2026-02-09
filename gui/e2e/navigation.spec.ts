import { test, expect } from "@playwright/test";

test.describe("Navigation", () => {
  test("navigates between Dashboard, Library, and Projects tabs", async ({
    page,
  }) => {
    await page.goto("/gui/");

    // Dashboard loads by default
    await expect(
      page.getByRole("heading", { name: "Dashboard" }),
    ).toBeVisible();

    // Navigate to Library
    await page.getByTestId("nav-tab-library").click();
    await expect(page).toHaveURL(/\/gui\/library/);
    await expect(
      page.getByRole("heading", { name: "Library" }),
    ).toBeVisible();

    // Navigate to Projects
    await page.getByTestId("nav-tab-projects").click();
    await expect(page).toHaveURL(/\/gui\/projects/);
    await expect(
      page.getByRole("heading", { name: "Projects" }),
    ).toBeVisible();

    // Navigate back to Dashboard
    await page.getByTestId("nav-tab-dashboard").click();
    await expect(page).toHaveURL(/\/gui\/?$/);
    await expect(
      page.getByRole("heading", { name: "Dashboard" }),
    ).toBeVisible();
  });
});
