import { test, expect } from "@playwright/test";

const events = [1, 2, 3].map((id) => ({
  id: String(id),
  title: `Событие ${id}`,
  category: "koncerty",
  category_name: "Концерты",
  image_url: null,
  start_date: "2026-10-01T18:00:00Z",
  end_date: "2026-10-01T20:00:00Z",
  timezone: "Europe/Moscow",
  location_name: "Парк",
  city: "Москва",
  address: "Центр",
  latitude: 55.75 + id / 100,
  longitude: 37.61,
  is_free: true,
  reasons: [],
  tags: [],
}));

test.beforeEach(async ({ page }) => {
  await page.route("https://st.max.ru/**", (route) =>
    route.fulfill({ body: "" }),
  );
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const data = path.endsWith("/config")
      ? { demo_mode: true, event_provider: "demo" }
      : path.endsWith("/auth/demo")
        ? {
            access_token: "test",
            user: { id: "test", city: "Москва", onboarding_completed: true },
          }
        : path.endsWith("/recommendations") || path.endsWith("/favorites")
          ? events
          : {};
    await route.fulfill({ json: data });
  });
});

test("short swipe returns; reaction animates once and shows next card without reloading", async ({
  page,
}) => {
  let posts = 0;
  let recommendations = 0;
  page.on("request", (r) => {
    if (r.url().endsWith("/recommendations")) recommendations++;
  });
  await page.route("**/reaction", async (route) => {
    posts++;
    await new Promise((resolve) => setTimeout(resolve, 450));
    await route.fulfill({ json: {} });
  });
  await page.goto("/discover");
  const card = page.locator(".swipe-card");
  await expect(card).toBeVisible();
  const initialRecommendations = recommendations;
  const box = (await page.locator(".hero-image").boundingBox())!;
  await page.mouse.move(box.x + 170, box.y + 60);
  await page.mouse.down();
  await page.mouse.move(box.x + 205, box.y + 60);
  await page.mouse.up();
  await expect(card).toHaveCSS("transform", "matrix(1, 0, 0, 1, 0, 0)");
  expect(posts).toBe(0);
  await page.getByRole("button", { name: "Нравится", exact: true }).click();
  await expect(card).toHaveAttribute("aria-busy", "true");
  await expect(
    page.getByRole("button", { name: "Нравится", exact: true }),
  ).toBeDisabled();
  await expect(card.locator("h2")).toHaveText("Событие 2");
  expect(posts).toBe(1);
  expect(recommendations).toBe(initialRecommendations);
  await page.mouse.move(box.x + 220, box.y + 60);
  await page.mouse.down();
  await page.mouse.move(box.x + 80, box.y + 62, { steps: 8 });
  await page.mouse.up();
  await expect(card.locator("h2")).toHaveText("Событие 3");
  expect(posts).toBe(2);
});

test("failed save restores card and reduced motion disables mascot animation", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.route("**/reaction", (route) =>
    route.fulfill({ status: 500, json: { detail: "Не удалось сохранить" } }),
  );
  await page.goto("/discover");
  await page.getByRole("button", { name: "Нравится", exact: true }).click();
  await expect(
    page.getByText("Не удалось сохранить", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".swipe-card h2")).toHaveText("Событие 1");
  await expect(page.locator(".swipe-card")).toHaveCSS("opacity", "1");
  await expect(page.locator(".mascot")).toHaveCSS("animation-name", "none");
  await expect(
    page.getByRole("button", { name: "Нравится", exact: true }),
  ).toBeEnabled();
});

test("OpenStreetMap markers open event details", async ({ page }) => {
  await page.route("https://*.tile.openstreetmap.org/**", (route) =>
    route.abort(),
  );
  await page.goto("/map");
  await expect(page.locator(".event-map.leaflet-container")).toBeVisible();
  await expect(page.locator(".event-pin")).toHaveCount(3);
  await page.locator(".event-pin").first().click();
  await page.locator(".leaflet-popup-content button").click();
  await expect(page).toHaveURL(/\/events\/1$/);
});
