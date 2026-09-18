import { test, expect, type Page } from "@playwright/test";
import type { EveningOptions, EveningPlan } from "../src/types";

const user = {
  id: "evening-user",
  first_name: "Друг",
  city: "Москва",
  onboarding_completed: true,
};
function makePlan(index: number, options: EveningOptions): EveningPlan {
  const events = [0, 1].map((offset) => ({
    id: `event-${index}-${offset}`,
    title: `Событие вечера ${index}-${offset}`,
    description: "Новые впечатления и интересная программа в центре города.",
    category: "kino",
    category_name: "Кино",
    tags: [],
    image_url: null,
    image_credit: null,
    start_date: `2030-01-05T${15 + offset}:00:00Z`,
    end_date: `2030-01-05T${15 + offset}:45:00Z`,
    timezone: "Europe/Moscow",
    price_min: options.budget_max === 0 ? 0 : 400,
    price_max: 400,
    estimated_price: options.budget_max === 0 ? 0 : 400,
    is_free: options.budget_max === 0,
    city: "Москва",
    location_name: "Киноклуб",
    address: "Центральная улица, 1",
    latitude: null,
    longitude: null,
    source_url: null,
    provider: "demo",
    reasons: ["По вашим интересам"],
    next_transfer: offset === 0 ? { distance_km: 0.2, minutes: 13 } : null,
  }));
  return {
    ...options,
    id: `plan-${index}`,
    saved: false,
    created_at: "2030-01-04T12:00:00Z",
    city: "Москва",
    date: "2030-01-05",
    events,
    event_count: 2,
    total_cost: options.budget_max === 0 ? 0 : 800,
    cost_complete: true,
    duration_minutes: 105,
    score: 0.7,
    score_components: { interests_match: 0.9 },
    reasons: ["Площадки рядом", "Можно посетить последовательно"],
    warnings: [],
  };
}
async function mockApp(page: Page) {
  let currentUser = { ...user };
  const plans = new Map<string, EveningPlan>();
  const generated: Record<string, unknown>[] = [];
  await page.route("https://st.max.ru/**", (route) =>
    route.fulfill({ body: "" }),
  );
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let data: unknown = {};
    if (path.endsWith("/config"))
      data = {
        demo_mode: true,
        event_provider: "demo",
        demo_cities: ["Москва", "Казань"],
      };
    else if (path.endsWith("/auth/demo"))
      data = { access_token: "test", user: currentUser };
    else if (path === "/api/v1/categories")
      data = [{ id: "kino", name: "Кино" }];
    else if (path.endsWith("/users/me/preferences")) {
      if (route.request().method() === "PUT") {
        currentUser = {
          ...currentUser,
          city: route.request().postDataJSON().city,
        };
        data = currentUser;
      } else
        data = {
          city: currentUser.city,
          categories: ["kino"],
          budget_max: 1000,
          companion: "friends",
          preferred_days: "any",
          preferred_time: "evening",
        };
    } else if (path.endsWith("/evenings/generate")) {
      const options = route.request().postDataJSON();
      generated.push(options);
      const plan = makePlan(generated.length, options);
      plans.set(plan.id, plan);
      data = { plan, reason: null };
    } else if (path.endsWith("/evenings"))
      data = [...plans.values()].filter((plan) => plan.saved);
    else if (/\/evenings\/plan-\d+\/save$/.test(path)) {
      const plan = plans.get(path.split("/").at(-2)!)!;
      plan.saved = true;
      data = plan;
    } else if (/\/evenings\/plan-\d+$/.test(path))
      data = plans.get(path.split("/").at(-1)!);
    else if (path.endsWith("/favorites") || path.endsWith("/recommendations"))
      data = [];
    else if (path.includes("/events/event-"))
      data = [...plans.values()]
        .flatMap((plan) => plan.events)
        .find((event) => path.endsWith("/" + event.id));
    await route.fulfill({ json: data });
  });
  return { generated, plans };
}
async function chooseEvening(page: Page, budget = "До 1000 ₽") {
  await page
    .getByRole("button", { name: "Спокойный вечер", exact: false })
    .click();
  await page.getByRole("button", { name: "Продолжить", exact: true }).click();
  await page.getByRole("button", { name: "1–2 часа", exact: true }).click();
  await page.getByRole("button", { name: "Продолжить", exact: true }).click();
  await page.getByRole("button", { name: budget, exact: true }).click();
  await page
    .getByRole("button", { name: "Собрать мой вечер", exact: true })
    .click();
}

test("three steps, route, details return, save and restore the whole evening", async ({
  page,
}) => {
  const { generated } = await mockApp(page);
  await page.goto("/discover");
  await page
    .getByRole("button", { name: "Собери мой вечер", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Продолжить", exact: true }),
  ).toBeDisabled();
  await expect(page.locator(".evening-choices button")).toHaveCount(6);
  await chooseEvening(page);
  expect(generated).toEqual([
    {
      vibe: "calm",
      duration_hours: 2,
      budget_max: 1000,
      excluded_plan_ids: [],
    },
  ]);
  await expect(page.locator(".evening-timeline > li")).toHaveCount(2);
  await expect(page.locator(".evening-summary")).toContainText("800");
  await expect(page.locator(".evening-summary")).toContainText("1 ч 45 мин");
  await expect(page.locator(".evening-transfer")).toContainText(
    "13 мин пешком",
  );
  await page
    .getByRole("button", { name: "Подробнее", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "Событие вечера 1-0" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Назад", exact: true }).click();
  await expect(page.locator(".evening-timeline > li")).toHaveCount(2);
  expect(generated).toHaveLength(1);
  await page.getByRole("button", { name: "Мне нравится", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Вечер сохранён", exact: true }),
  ).toBeDisabled();
  await page.getByRole("link", { name: "Мои события", exact: true }).click();
  await expect(page.locator(".saved-evening")).toHaveCount(1);
  await page.locator(".saved-evening").click();
  await expect(page).toHaveURL(/\/evenings\/plan-1$/);
  await expect(page.locator(".evening-timeline h3")).toHaveText([
    "Событие вечера 1-0",
    "Событие вечера 1-1",
  ]);
  await page
    .getByRole("button", { name: "Собрать новый вечер", exact: false })
    .click();
  await expect(
    page.getByRole("heading", { name: "Какой вайб выбираем?" }),
  ).toBeVisible();
  await expect(page.locator(".evening-timeline")).toHaveCount(0);
});

test("another evening excludes previous plans and exhaustion retains the result", async ({
  page,
}) => {
  const { generated } = await mockApp(page);
  await page.goto("/evening");
  await chooseEvening(page);
  await page
    .getByRole("button", { name: "Собрать другой", exact: true })
    .click();
  await expect(page.locator(".evening-timeline h3").first()).toHaveText(
    "Событие вечера 2-0",
  );
  expect(generated[1].excluded_plan_ids).toEqual(["plan-1"]);
  await page.route("**/evenings/generate", (route) =>
    route.fulfill({ json: { plan: null, reason: "exhausted" } }),
  );
  await page
    .getByRole("button", { name: "Собрать другой", exact: true })
    .click();
  await expect(
    page.getByText(/Другие варианты с этими условиями закончились/),
  ).toBeVisible();
  await expect(page.locator(".evening-timeline h3").first()).toHaveText(
    "Событие вечера 2-0",
  );
});

test("empty state and generation errors permit changing conditions and retry", async ({
  page,
}) => {
  await mockApp(page);
  await page.route("**/evenings/generate", (route) =>
    route.fulfill({ json: { plan: null, reason: "no_matches" } }),
  );
  await page.goto("/evening");
  await chooseEvening(page, "Бесплатно");
  await expect(
    page.getByRole("heading", { name: "Не получилось собрать вечер" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Изменить условия", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Какой вайб выбираем?" }),
  ).toBeVisible();
  await page.unroute("**/evenings/generate");
  await page.route("**/evenings/generate", (route) =>
    route.fulfill({ status: 502, json: { detail: "Источник недоступен" } }),
  );
  await chooseEvening(page);
  await expect(page.getByRole("alert")).toHaveText("Источник недоступен");
  await page.unroute("**/evenings/generate");
  await page
    .getByRole("button", { name: "Собрать мой вечер", exact: true })
    .click();
  await expect(page.locator(".evening-timeline > li")).toHaveCount(2);
});

test("failed save and regeneration retain route and loading prevents duplicate requests", async ({
  page,
}) => {
  await mockApp(page);
  await page.goto("/evening");
  await chooseEvening(page);
  await page.route("**/evenings/plan-1/save", (route) =>
    route.fulfill({
      status: 500,
      json: { detail: "Не удалось сохранить вечер" },
    }),
  );
  await page.getByRole("button", { name: "Мне нравится", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText(
    "Не удалось сохранить вечер",
  );
  await expect(
    page.getByRole("button", { name: "Мне нравится", exact: true }),
  ).toBeEnabled();
  await page.unroute("**/evenings/plan-1/save");
  await page.getByRole("button", { name: "Мне нравится", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Вечер сохранён", exact: true }),
  ).toBeDisabled();
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  let requests = 0;
  await page.route("**/evenings/generate", async (route) => {
    requests++;
    await gate;
    await route.fulfill({
      status: 502,
      json: { detail: "Не удалось собрать другой вечер" },
    });
  });
  await page
    .getByRole("button", { name: "Собрать другой", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Собираю…", exact: true }),
  ).toBeDisabled();
  release();
  await expect(page.getByRole("alert")).toHaveText(
    "Не удалось собрать другой вечер",
  );
  expect(requests).toBe(1);
  await expect(page.locator(".evening-timeline > li")).toHaveCount(2);
});

test("changing profile city resets the unsaved route", async ({ page }) => {
  await mockApp(page);
  await page.goto("/evening");
  await chooseEvening(page);
  await page.getByRole("link", { name: "Мой вкус", exact: true }).click();
  await page.getByLabel("В каком городе ищем?").selectOption("Казань");
  await page.getByRole("button", { name: /Сохранить предпочтения/ }).click();
  await page.getByRole("button", { name: /Собери мой вечер/ }).click();
  await expect(page.locator(".evening-timeline")).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Какой вайб выбираем?" }),
  ).toBeVisible();
  await expect(page.locator(".evening-page .subtitle")).toContainText("Казань");
});

for (const width of [360, 390, 520]) {
  test(`evening wizard and route fit ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await mockApp(page);
    await page.goto("/evening");
    await expect(page.locator("body")).toHaveJSProperty("scrollWidth", width);
    await page.screenshot({
      path: `test-results/evening-wizard-${width}.png`,
      fullPage: true,
    });
    await chooseEvening(page);
    await expect(page.locator(".evening-timeline > li")).toHaveCount(2);
    await expect(page.locator(".evening-actions")).toBeVisible();
    await expect(page.locator("body")).toHaveJSProperty("scrollWidth", width);
    await page.screenshot({
      path: `test-results/evening-route-${width}.png`,
      fullPage: true,
    });
  });
}

test("real demo source generates and saves a feasible free evening", async ({
  page,
  request,
}) => {
  await page.route("https://st.max.ru/**", (route) =>
    route.fulfill({ body: "" }),
  );
  const auth = await (await request.post("/api/v1/auth/demo")).json();
  const headers = { Authorization: `Bearer ${auth.access_token}` };
  await request.put("/api/v1/users/me/preferences", {
    headers,
    data: {
      city: "Москва",
      categories: ["vystavki", "koncerty"],
      budget_max: 1500,
    },
  });
  await page.goto("/evening");
  await chooseEvening(page, "Бесплатно");
  await expect(page.locator(".evening-timeline > li")).toHaveCount(2);
  await expect(page.locator(".evening-summary")).toContainText("Бесплатно");
  const response = page.waitForResponse((r) =>
    /\/evenings\/[^/]+\/save$/.test(new URL(r.url()).pathname),
  );
  await page.getByRole("button", { name: "Мне нравится", exact: true }).click();
  expect((await response).status()).toBe(200);
  await expect(
    page.getByRole("button", { name: "Вечер сохранён", exact: true }),
  ).toBeDisabled();
  await page.getByRole("link", { name: "Мои события", exact: true }).click();
  await expect(page.locator(".saved-evening").first()).toBeVisible();
});
