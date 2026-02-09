import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

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
});
