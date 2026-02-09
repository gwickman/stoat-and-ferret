import { test, expect } from "@playwright/test";

test.describe("Library scan", () => {
  test("triggers scan from library browser and shows feedback", async ({
    page,
  }) => {
    // Navigate to library via client-side routing (SPA)
    await page.goto("/gui/");
    await page.getByTestId("nav-tab-library").click();
    await expect(
      page.getByRole("heading", { name: "Library" }),
    ).toBeVisible();

    // Open scan modal
    await page.getByTestId("scan-button").click();
    await expect(page.getByTestId("scan-modal-overlay")).toBeVisible();

    // Enter directory path
    await page.getByTestId("scan-directory-input").fill("/tmp/test-videos");

    // Submit the scan
    await page.getByTestId("scan-submit").click();

    // Verify scan feedback appears (progress indicator or error for non-existent dir)
    await expect(
      page
        .getByTestId("scan-progress")
        .or(page.getByTestId("scan-complete"))
        .or(page.getByTestId("scan-error")),
    ).toBeVisible({ timeout: 10000 });
  });
});
