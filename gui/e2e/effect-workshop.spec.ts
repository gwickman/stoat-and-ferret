import { test, expect, type Page, type APIRequestContext } from "@playwright/test";
import { execSync } from "child_process";
import { mkdtempSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";

// --- Environment checks ---

function ffmpegAvailable(): boolean {
  try {
    execSync("ffmpeg -version", { stdio: "pipe", timeout: 5000 });
    return true;
  } catch {
    return false;
  }
}

const HAS_FFMPEG = ffmpegAvailable();

// --- Helpers ---

/** Check that the effects API is working (requires Rust module). */
async function checkEffectsApi(request: APIRequestContext): Promise<boolean> {
  try {
    const res = await request.get("/api/v1/effects");
    return res.ok();
  } catch {
    return false;
  }
}

/** Navigate to the Effects page via client-side routing (SPA). */
async function navigateToEffects(page: Page) {
  await page.goto("/gui/");
  await page.getByTestId("nav-tab-effects").click();
  await expect(page.getByRole("heading", { name: "Effects" })).toBeVisible();
  // Wait for catalog (may take longer in CI due to cold start)
  await expect(page.getByTestId("effect-catalog")).toBeVisible({
    timeout: 15_000,
  });
}

/** Navigate to effects page and select a specific project's clip. */
async function navigateAndSelectClip(
  page: Page,
  projectId: string,
  clipId: string,
) {
  await navigateToEffects(page);

  // Select correct project if multiple projects exist
  const projectSelect = page.getByTestId("project-select");
  if ((await projectSelect.count()) > 0) {
    await projectSelect.selectOption(projectId);
  }

  // Wait for clip to load and select it
  await expect(page.getByTestId(`clip-option-${clipId}`)).toBeVisible({
    timeout: 10_000,
  });
  await page.getByTestId(`clip-option-${clipId}`).click();
}

/** Create a project with a clip via API, returning IDs. */
async function setupProjectWithClip(
  request: APIRequestContext,
): Promise<{ projectId: string; clipId: string }> {
  // Generate a minimal test video with ffmpeg
  const videoDir = mkdtempSync(join(tmpdir(), "e2e-effects-"));
  const videoPath = join(videoDir, "test.mp4");
  execSync(
    `ffmpeg -f lavfi -i testsrc=duration=1:size=320x240:rate=24 -f lavfi -i sine=frequency=440:duration=1 -c:v libx264 -c:a aac -y "${videoPath}"`,
    { timeout: 30_000, stdio: "pipe" },
  );

  // Scan the directory to register the video
  const scanRes = await request.post("/api/v1/videos/scan", {
    data: { path: videoDir, recursive: false },
  });
  expect(scanRes.ok()).toBeTruthy();
  const { job_id } = await scanRes.json();

  // Poll until scan completes
  for (let i = 0; i < 60; i++) {
    const jobRes = await request.get(`/api/v1/jobs/${job_id}`);
    const job = await jobRes.json();
    if (job.status === "complete") break;
    await new Promise((r) => setTimeout(r, 500));
  }

  // Get the registered video ID
  const videosRes = await request.get("/api/v1/videos");
  const { videos } = await videosRes.json();
  expect(videos.length).toBeGreaterThan(0);
  const videoId = videos[videos.length - 1].id;

  // Create a project
  const projRes = await request.post("/api/v1/projects", {
    data: {
      name: `E2E Effects ${Date.now()}`,
      output_width: 1920,
      output_height: 1080,
      output_fps: 30,
    },
  });
  expect(projRes.ok()).toBeTruthy();
  const project = await projRes.json();

  // Create a clip on the project
  const clipRes = await request.post(
    `/api/v1/projects/${project.id}/clips`,
    {
      data: {
        source_video_id: videoId,
        in_point: 0,
        out_point: 10,
        timeline_position: 0,
      },
    },
  );
  expect(clipRes.ok()).toBeTruthy();
  const clip = await clipRes.json();

  return { projectId: project.id, clipId: clip.id };
}

// --- FR-001: Browse catalog and select effect ---

test.describe("Effect Workshop - Catalog", () => {
  test("browses effect catalog and selects an effect", async ({
    page,
    request,
  }) => {
    const apiOk = await checkEffectsApi(request);
    test.skip(!apiOk, "Effects API unavailable (Rust module not built)");

    await navigateToEffects(page);

    // Catalog displays effect cards
    const cardList = page.getByTestId("effect-card-list");
    await expect(cardList).toBeVisible();
    await expect(
      cardList.locator("[data-testid^='effect-card-']").first(),
    ).toBeVisible();

    // Search filters effects
    await page.getByTestId("effect-search-input").fill("volume");
    await expect(page.getByTestId("effect-card-volume")).toBeVisible();

    // Clear search and filter by category
    await page.getByTestId("effect-search-input").clear();
    await page.getByTestId("effect-category-filter").selectOption("audio");
    await expect(page.getByTestId("effect-card-volume")).toBeVisible();

    // Reset category filter
    await page.getByTestId("effect-category-filter").selectOption("");

    // Click to select an effect — parameter form appears
    await page.getByTestId("effect-card-volume").click();
    await expect(page.getByTestId("effect-parameter-form")).toBeVisible();
  });
});

// --- FR-002: Configure parameters and verify preview ---

test.describe("Effect Workshop - Parameters and Preview", () => {
  test("configures parameters and verifies filter preview updates", async ({
    page,
    request,
  }) => {
    const apiOk = await checkEffectsApi(request);
    test.skip(!apiOk, "Effects API unavailable (Rust module not built)");

    await navigateToEffects(page);

    // Select volume effect
    await page.getByTestId("effect-card-volume").click();
    await expect(page.getByTestId("effect-parameter-form")).toBeVisible();
    await expect(page.getByTestId("field-volume")).toBeVisible();

    // Change the volume parameter
    await page.getByTestId("input-volume").fill("2");

    // Filter preview updates after debounce (~300ms)
    await expect(page.getByTestId("filter-preview")).toBeVisible();
    await expect(page.getByTestId("filter-string")).toContainText("volume", {
      timeout: 5000,
    });
  });
});

// --- FR-003 / FR-004: Apply, edit, remove effects ---

test.describe("Effect Workshop - Apply, Edit, Remove", () => {
  test.describe.configure({ mode: "serial" });

  let projectId: string;
  let clipId: string;
  let initialized = false;

  async function ensureSetup(request: APIRequestContext) {
    if (initialized) return;
    const setup = await setupProjectWithClip(request);
    projectId = setup.projectId;
    clipId = setup.clipId;
    initialized = true;
  }

  test("applies effect to clip and verifies effect stack", async ({
    page,
    request,
  }) => {
    const apiOk = await checkEffectsApi(request);
    test.skip(!apiOk, "Effects API unavailable (Rust module not built)");
    test.skip(!HAS_FFMPEG, "ffmpeg required for clip setup");

    await ensureSetup(request);
    await navigateAndSelectClip(page, projectId, clipId);

    // Select volume effect and set parameter
    await page.getByTestId("effect-card-volume").click();
    await expect(page.getByTestId("effect-parameter-form")).toBeVisible();
    await page.getByTestId("input-volume").fill("2");

    // Apply effect to the clip
    await page.getByTestId("apply-effect-btn").click();
    await expect(page.getByTestId("apply-status")).toContainText(
      "Effect applied!",
    );

    // Effect appears in the stack
    await expect(page.getByTestId("effect-stack")).toBeVisible();
    await expect(page.getByTestId("effect-entry-0")).toBeVisible();
    await expect(page.getByTestId("effect-type-0")).toContainText("volume");
  });

  test("edits applied effect with pre-filled form", async ({
    page,
    request,
  }) => {
    const apiOk = await checkEffectsApi(request);
    test.skip(!apiOk, "Effects API unavailable (Rust module not built)");
    test.skip(!HAS_FFMPEG, "ffmpeg required for clip setup");

    await ensureSetup(request);
    await navigateAndSelectClip(page, projectId, clipId);

    // Wait for effect stack with the previously applied effect
    await expect(page.getByTestId("effect-stack")).toBeVisible();
    await expect(page.getByTestId("effect-entry-0")).toBeVisible();

    // Click edit on the applied effect
    await page.getByTestId("edit-effect-0").click();

    // Parameter form opens; button says "Update Effect"
    await expect(page.getByTestId("effect-parameter-form")).toBeVisible();
    await expect(page.getByTestId("apply-effect-btn")).toContainText(
      "Update Effect",
    );

    // Update the volume parameter and save
    await page.getByTestId("input-volume").fill("3");
    await page.getByTestId("apply-effect-btn").click();

    await expect(page.getByTestId("apply-status")).toContainText(
      "Effect updated!",
    );
  });

  test("removes applied effect with confirmation dialog", async ({
    page,
    request,
  }) => {
    const apiOk = await checkEffectsApi(request);
    test.skip(!apiOk, "Effects API unavailable (Rust module not built)");
    test.skip(!HAS_FFMPEG, "ffmpeg required for clip setup");

    await ensureSetup(request);
    await navigateAndSelectClip(page, projectId, clipId);

    // Wait for the effect in the stack
    await expect(page.getByTestId("effect-stack")).toBeVisible();
    await expect(page.getByTestId("effect-entry-0")).toBeVisible();

    // Click remove — confirmation dialog appears
    await page.getByTestId("remove-effect-0").click();
    await expect(page.getByTestId("confirm-delete-0")).toBeVisible();

    // Confirm deletion
    await page.getByTestId("confirm-yes-0").click();

    // Stack shows empty state
    await expect(page.getByTestId("effect-stack-empty")).toBeVisible();
  });
});

// --- FR-005 (partial): Keyboard navigation ---

test.describe("Effect Workshop - Keyboard Navigation", () => {
  test("navigates full workflow with Tab, Enter, and Space", async ({
    page,
    request,
  }) => {
    const apiOk = await checkEffectsApi(request);
    test.skip(!apiOk, "Effects API unavailable (Rust module not built)");

    await navigateToEffects(page);

    // Select effect via Enter key
    const volumeCard = page.getByTestId("effect-card-volume");
    await volumeCard.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByTestId("effect-parameter-form")).toBeVisible();

    // Tab through form inputs
    const formInputs = page
      .getByTestId("effect-parameter-form")
      .locator("input, select");
    const inputCount = await formInputs.count();
    expect(inputCount).toBeGreaterThan(0);

    await formInputs.first().focus();
    for (let i = 0; i < inputCount - 1; i++) {
      await page.keyboard.press("Tab");
    }

    // Select a different effect via Space key
    const textCard = page.getByTestId("effect-card-text_overlay");
    await textCard.focus();
    await page.keyboard.press("Space");

    // Parameter form updates for the new effect
    await expect(page.getByTestId("field-text")).toBeVisible();
  });
});
