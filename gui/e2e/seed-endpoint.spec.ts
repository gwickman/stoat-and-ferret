import { test, expect, type APIRequestContext } from "@playwright/test";

interface SeedResponse {
  fixture_id: string;
  fixture_type: string;
  name: string;
}

async function createSeedFixture(
  request: APIRequestContext,
  name: string,
  outputWidth = 1920,
  outputHeight = 1080,
): Promise<SeedResponse> {
  const res = await request.post("/api/v1/testing/seed", {
    data: {
      fixture_type: "project",
      name,
      data: { output_width: outputWidth, output_height: outputHeight, output_fps: 30 },
    },
  });
  expect(res.status()).toBe(201);
  return res.json() as Promise<SeedResponse>;
}

async function deleteSeedFixture(
  request: APIRequestContext,
  fixtureId: string,
): Promise<void> {
  const res = await request.delete(
    `/api/v1/testing/seed/${fixtureId}?fixture_type=project`,
  );
  expect(res.status()).toBe(204);
}

test.describe("J606: Seed Endpoint API", () => {
  test(
    "FR-003: POST seed creates project fixture with seeded_ prefix and correct schema",
    async ({ request }) => {
      const baseName = `e2e_schema_${Date.now()}`;
      let fixtureId: string | null = null;

      try {
        const res = await request.post("/api/v1/testing/seed", {
          data: {
            fixture_type: "project",
            name: baseName,
            data: { output_width: 1920, output_height: 1080, output_fps: 30 },
          },
        });

        // HTTP 201 Created
        expect(res.status()).toBe(201);

        const body = (await res.json()) as SeedResponse;
        fixtureId = body.fixture_id;

        // Response schema: fixture_id, fixture_type, name
        expect(typeof body.fixture_id).toBe("string");
        expect(body.fixture_id.length).toBeGreaterThan(0);
        expect(body.fixture_type).toBe("project");

        // Server prepends seeded_ prefix (INV-SEED-2)
        expect(body.name).toBe(`seeded_${baseName}`);

        // Fixture is queryable via projects API
        const projectRes = await request.get(
          `/api/v1/projects/${body.fixture_id}`,
        );
        expect(projectRes.status()).toBe(200);

        const project = (await projectRes.json()) as {
          id: string;
          name: string;
          output_width: number;
          output_height: number;
          output_fps: number;
        };
        expect(project.id).toBe(body.fixture_id);
        expect(project.name).toBe(`seeded_${baseName}`);
        expect(project.output_width).toBe(1920);
        expect(project.output_height).toBe(1080);
        expect(project.output_fps).toBe(30);
      } finally {
        if (fixtureId) await deleteSeedFixture(request, fixtureId);
      }
    },
  );

  test(
    "FR-004: DELETE seed fixture returns 204 and removes it from API",
    async ({ request }) => {
      const baseName = `e2e_delete_${Date.now()}`;
      const fixture = await createSeedFixture(request, baseName);

      // Delete the fixture
      const deleteRes = await request.delete(
        `/api/v1/testing/seed/${fixture.fixture_id}?fixture_type=project`,
      );
      expect(deleteRes.status()).toBe(204);

      // Fixture is no longer accessible via projects API
      const getRes = await request.get(
        `/api/v1/projects/${fixture.fixture_id}`,
      );
      expect(getRes.status()).toBe(404);
    },
  );

  test(
    "FR-005: create 3 fixtures with different sizes, verify in projects page, delete all",
    async ({ page, request }) => {
      const suffix = Date.now();
      const fixtureNames = [
        `e2e_lib_1920_${suffix}`,
        `e2e_lib_1280_${suffix}`,
        `e2e_lib_640_${suffix}`,
      ];
      const sizes = [
        { w: 1920, h: 1080 },
        { w: 1280, h: 720 },
        { w: 640, h: 480 },
      ];

      const fixtures: SeedResponse[] = [];

      try {
        // Create 3 fixtures with distinct output sizes
        for (let i = 0; i < 3; i++) {
          const f = await createSeedFixture(
            request,
            fixtureNames[i],
            sizes[i].w,
            sizes[i].h,
          );
          fixtures.push(f);
        }

        // Navigate to projects page
        await page.goto("/?workspace=edit");
        await page.getByTestId("nav-tab-projects").click();
        await expect(page).toHaveURL(/\/gui\/projects/);
        await expect(page.getByTestId("projects-page")).toBeVisible();

        // Wait for project list to load
        await expect(page.getByTestId("project-list")).toBeVisible({
          timeout: 10_000,
        });

        // All 3 seeded projects appear with seeded_ prefix
        for (let i = 0; i < 3; i++) {
          const expectedName = `seeded_${fixtureNames[i]}`;
          await expect(page.getByText(expectedName)).toBeVisible();
        }

        // Delete all fixtures
        for (const fixture of fixtures) {
          await deleteSeedFixture(request, fixture.fixture_id);
        }
        fixtures.length = 0;

        // Reload and verify fixtures are gone
        await page.reload();
        await expect(page.getByTestId("projects-page")).toBeVisible();

        for (let i = 0; i < 3; i++) {
          const expectedName = `seeded_${fixtureNames[i]}`;
          await expect(page.getByText(expectedName)).not.toBeVisible();
        }
      } finally {
        // Best-effort cleanup for any fixtures not yet deleted
        for (const fixture of fixtures) {
          try {
            await request.delete(
              `/api/v1/testing/seed/${fixture.fixture_id}?fixture_type=project`,
            );
          } catch {
            // ignore cleanup errors
          }
        }
      }
    },
  );

  test(
    "NFR-002: multiple POST requests with same name create separate fixtures",
    async ({ request }) => {
      const baseName = `e2e_idempotent_${Date.now()}`;
      let fixture1: SeedResponse | null = null;
      let fixture2: SeedResponse | null = null;

      try {
        fixture1 = await createSeedFixture(request, baseName);
        fixture2 = await createSeedFixture(request, baseName);

        // Name is not a unique key — both requests succeed with distinct IDs
        expect(fixture1.fixture_id).not.toBe(fixture2.fixture_id);
        expect(fixture1.name).toBe(`seeded_${baseName}`);
        expect(fixture2.name).toBe(`seeded_${baseName}`);
      } finally {
        if (fixture1) {
          try {
            await request.delete(
              `/api/v1/testing/seed/${fixture1.fixture_id}?fixture_type=project`,
            );
          } catch {
            // ignore
          }
        }
        if (fixture2) {
          try {
            await request.delete(
              `/api/v1/testing/seed/${fixture2.fixture_id}?fixture_type=project`,
            );
          } catch {
            // ignore
          }
        }
      }
    },
  );
});
