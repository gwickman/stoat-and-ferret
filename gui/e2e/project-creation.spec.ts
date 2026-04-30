import { test, expect } from "@playwright/test";

test.describe("Project creation", () => {
  test("creates a project via modal and verifies it appears in list", async ({
    page,
  }) => {
    // BL-306: ProjectsPage is not yet assigned to a workspace panel preset.
    // The panel routing model (PRESETS routes) currently covers only:
    // library, timeline, effects, preview, render-queue, batch.
    // Until ProjectsPage is mapped to a panel, this test cannot navigate to it.
    // TODO: assign ProjectsPage to a panel preset and remove this skip.
    test.skip(true, "BL-306: ProjectsPage needs a workspace panel assignment before this test can run.");

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
    const created = page.waitForResponse(
      (resp) =>
        resp.url().includes("/api/v1/projects") &&
        resp.request().method() === "POST",
    );
    await page.getByTestId("btn-create").click();
    await created;

    // Modal closes and project appears in the list.
    await expect(page.getByTestId("create-project-modal")).toBeHidden({ timeout: 10_000 });
    await expect(page.getByText(projectName)).toBeVisible();
  });
});
