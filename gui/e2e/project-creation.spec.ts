import { test, expect } from "@playwright/test";

test.describe("Project creation", () => {
  test("creates a project via modal and verifies it appears in list", async ({
    page,
  }) => {
    // Navigate to projects via client-side routing (SPA)
    await page.goto("/gui/");
    await page.getByTestId("nav-tab-projects").click();
    await expect(
      page.getByRole("heading", { name: "Projects" }),
    ).toBeVisible();

    const projectName = `E2E Test Project ${Date.now()}`;

    // Open create project modal
    await page.getByTestId("btn-new-project").click();
    await expect(page.getByTestId("create-project-modal")).toBeVisible();

    // Fill in project details
    await page.getByTestId("input-project-name").fill(projectName);
    await page.getByTestId("input-resolution").clear();
    await page.getByTestId("input-resolution").fill("1920x1080");
    await page.getByTestId("input-fps").clear();
    await page.getByTestId("input-fps").fill("30");

    // Submit and wait for the API response before checking modal state.
    // The modal only closes after the POST completes; in CI the backend
    // can be slow, so the default assertion timeout is not enough.
    const created = page.waitForResponse(
      (resp) =>
        resp.url().includes("/api/v1/projects") &&
        resp.request().method() === "POST",
    );
    await page.getByTestId("btn-create").click();
    await created;

    // Modal closes and project appears in the list.
    // The modal close depends on React re-render after the POST response;
    // in CI the server can be slow, so use an explicit timeout (BL-055).
    await expect(page.getByTestId("create-project-modal")).toBeHidden({
      timeout: 10000,
    });
    await expect(page.getByText(projectName)).toBeVisible({ timeout: 5000 });
  });
});
