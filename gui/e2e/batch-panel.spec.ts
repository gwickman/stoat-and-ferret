import { test, expect, type APIRequestContext } from "@playwright/test";

interface ProjectResponse {
  id: string;
  name: string;
  output_width: number;
  output_height: number;
  output_fps: number;
}

async function createTestProject(
  request: APIRequestContext,
  name: string,
): Promise<ProjectResponse> {
  const res = await request.post("/api/v1/projects", {
    data: { name, output_width: 1920, output_height: 1080, output_fps: 30 },
  });
  expect(res.status()).toBe(201);
  return res.json() as Promise<ProjectResponse>;
}

async function deleteTestProject(
  request: APIRequestContext,
  projectId: string,
): Promise<void> {
  await request.delete(`/api/v1/projects/${projectId}`);
}

test.describe("J603: Batch Panel WebSocket Events", () => {
  test(
    "FR-001: batch form submission succeeds and job appears in list",
    async ({ page, request }) => {
      const projectName = `batch_e2e_fr001_${Date.now()}`;
      const project = await createTestProject(request, projectName);

      try {
        // Navigate directly to /render — single RenderPage instance, no dual-panel strict-mode violation
        await page.goto("/gui/render");
        await expect(page.getByTestId("render-tabs")).toBeVisible();

        // Batch tab requires batch_rendering flag (defaults to true)
        const batchTab = page.getByTestId("render-tab-batch");
        await expect(batchTab).toBeVisible({ timeout: 10_000 });
        await batchTab.click();

        await expect(
          page.getByTestId("render-tab-batch-content"),
        ).toBeVisible();
        await expect(page.getByTestId("batch-panel")).toBeVisible();

        // Fill form: project ID, output path (quality defaults to "medium")
        await page.getByTestId("batch-project-0").fill(project.id);
        await page
          .getByTestId("batch-output-0")
          .fill("/tmp/e2e_batch_output_fr001.mp4");

        // Submit and capture response
        const submitPromise = page.waitForResponse(
          (resp) =>
            resp.url().includes("/api/v1/render/batch") &&
            resp.request().method() === "POST",
        );
        await page.getByTestId("batch-submit").click();
        const submitResponse = await submitPromise;

        // HTTP 202 Accepted with correct body
        expect(submitResponse.status()).toBe(202);
        const submitBody = (await submitResponse.json()) as {
          batch_id: string;
          jobs_queued: number;
          status: string;
        };
        expect(typeof submitBody.batch_id).toBe("string");
        expect(submitBody.jobs_queued).toBe(1);

        // No validation or server errors
        await expect(
          page.getByTestId("batch-validation-error"),
        ).not.toBeVisible();
        await expect(
          page.getByTestId("batch-submit-error"),
        ).not.toBeVisible();

        // Job row appears in BatchJobList
        await expect(page.getByTestId("batch-job-list")).toBeVisible({
          timeout: 5_000,
        });
        const jobRows = page.locator('[data-testid^="batch-job-row-"]');
        await expect(jobRows).toHaveCount(1, { timeout: 5_000 });
      } finally {
        await deleteTestProject(request, project.id);
      }
    },
  );

  test(
    "FR-002: progress bar and status badge appear after batch submission",
    async ({ page, request }) => {
      const projectName = `batch_e2e_fr002_${Date.now()}`;
      const project = await createTestProject(request, projectName);

      try {
        await page.goto("/gui/render");
        await expect(page.getByTestId("render-tabs")).toBeVisible();

        const batchTab = page.getByTestId("render-tab-batch");
        await expect(batchTab).toBeVisible({ timeout: 10_000 });
        await batchTab.click();
        await expect(page.getByTestId("batch-panel")).toBeVisible();

        // Collect WebSocket frames to check for render_progress events
        const wsFrames: unknown[] = [];
        page.on("websocket", (ws) => {
          ws.on("framereceived", (frame) => {
            try {
              wsFrames.push(JSON.parse(frame.payload as string));
            } catch {
              // ignore non-JSON frames
            }
          });
        });

        // Fill form
        await page.getByTestId("batch-project-0").fill(project.id);
        await page
          .getByTestId("batch-output-0")
          .fill("/tmp/e2e_batch_output_fr002.mp4");

        // Submit
        const submitPromise = page.waitForResponse(
          (resp) =>
            resp.url().includes("/api/v1/render/batch") &&
            resp.request().method() === "POST",
        );
        await page.getByTestId("batch-submit").click();
        const submitResponse = await submitPromise;
        expect(submitResponse.status()).toBe(202);

        // Job appears in list
        await expect(page.getByTestId("batch-job-list")).toBeVisible({
          timeout: 5_000,
        });
        const jobRows = page.locator('[data-testid^="batch-job-row-"]');
        await expect(jobRows).toHaveCount(1, { timeout: 5_000 });

        // Read job_id from the row's data-testid attribute
        const jobRowTestId =
          (await jobRows.first().getAttribute("data-testid")) ?? "";
        const jobId = jobRowTestId.replace("batch-job-row-", "");

        // Status badge and percentage text are visible immediately.
        // batch-progress-bar is the inner fill div; at 0% progress its width is
        // 0px and Playwright reports it as hidden — assert the pct text instead.
        await expect(
          page.getByTestId(`batch-status-${jobId}`),
        ).toBeVisible();
        await expect(
          page.getByTestId(`batch-progress-pct-${jobId}`),
        ).toBeVisible();

        // Allow time for job processing and WebSocket events to arrive
        await page.waitForTimeout(5_000);

        // If render_progress WebSocket events arrived, verify their schema
        const renderProgressEvents = wsFrames.filter(
          (
            frame,
          ): frame is { type: string; payload: Record<string, unknown> } =>
            typeof frame === "object" &&
            frame !== null &&
            (frame as Record<string, unknown>)["type"] === "render_progress",
        );

        if (renderProgressEvents.length > 0) {
          const event = renderProgressEvents[0];
          const p = event.payload;
          expect(typeof p["job_id"]).toBe("string");
          expect(typeof p["progress"]).toBe("number");
          expect(p["progress"] as number).toBeGreaterThanOrEqual(0);
          expect(p["progress"] as number).toBeLessThanOrEqual(100);
          expect(typeof p["eta_seconds"]).toBe("number");
          expect(typeof p["speed_ratio"]).toBe("number");
          expect(typeof p["frame_count"]).toBe("number");
          expect(typeof p["fps"]).toBe("number");
          expect(typeof p["encoder_name"]).toBe("string");
          expect(typeof p["encoder_type"]).toBe("string");
        }
      } finally {
        await deleteTestProject(request, project.id);
      }
    },
  );
});
