import { test, expect, type Page } from "@playwright/test";

const events = Array.from({ length: 25 }, (_, i) => ({
  id: String(i + 1),
  title:
    i === 0
      ? "Длинное название выставки о городе, искусстве и новых впечатлениях"
      : `Событие ${i + 1}`,
  description: "Описание события",
  category: i % 2 ? "koncerty" : "vystavki",
  category_name: i % 2 ? "Концерты" : "Выставки",
  image_url: null,
  image_credit: null,
  start_date: "2026-10-01T16:00:00Z",
  end_date: "2026-10-01T20:00:00Z",
  timezone: "Europe/Moscow",
  location_name: "Галерея городских историй",
  city: "Москва",
  address: "Центр",
  latitude: null,
  longitude: null,
  is_free: i % 3 === 0,
  price_min: i % 3 === 0 ? 0 : 500,
  price_max: 1000,
  reasons: [],
  tags: [],
  provider: "demo",
  source_url: null,
}));
const categories = [
  { id: "koncerty", name: "Концерты" },
  { id: "vystavki", name: "Выставки" },
  { id: "ekskursii", name: "Экскурсии" },
];

async function mockApp(page: Page, available = categories) {
  const saved = new Set<string>();
  const requests: URL[] = [];
  await page.route("https://st.max.ru/**", (route) =>
    route.fulfill({ body: "" }),
  );
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request(),
      url = new URL(request.url()),
      path = url.pathname;
    let data: unknown = {};
    if (path.endsWith("/config"))
      data = { demo_mode: true, event_provider: "demo" };
    else if (path.endsWith("/auth/demo"))
      data = {
        access_token: "test",
        user: {
          id: "catalog-user",
          city: "Москва",
          onboarding_completed: true,
        },
      };
    else if (path === "/api/v1/evenings") data = [];
    else if (path.endsWith("/categories")) data = available;
    else if (path.endsWith("/recommendations"))
      data = events.filter((event) => !saved.has(event.id));
    else if (path.endsWith("/favorites"))
      data = events.filter((event) => saved.has(event.id));
    else if (path.endsWith("/catalog")) {
      requests.push(url);
      let filtered = [...events];
      const q = (url.searchParams.get("q") || "").toLocaleLowerCase(),
        ids = url.searchParams.getAll("categories");
      if (q)
        filtered = filtered.filter((event) =>
          `${event.title} ${event.location_name}`
            .toLocaleLowerCase()
            .includes(q),
        );
      if (ids.length)
        filtered = filtered.filter((event) => ids.includes(event.category));
      if (url.searchParams.get("free_only") === "true")
        filtered = filtered.filter((event) => event.is_free);
      const offset = Number(url.searchParams.get("offset") || 0);
      data = {
        items: filtered
          .slice(offset, offset + 20)
          .map((event) => ({ ...event, is_saved: saved.has(event.id) })),
        total: filtered.length,
        has_more: offset + 20 < filtered.length,
      };
    } else if (path.endsWith("/reaction")) {
      const id = path.split("/").at(-2)!;
      if (request.method() === "DELETE") saved.delete(id);
      else saved.add(id);
    } else if (/\/events\/\d+$/.test(path))
      data = events.find((event) => event.id === path.split("/").at(-1));
    await route.fulfill({ json: data });
  });
  return { saved, requests };
}
async function openCatalog(page: Page) {
  await page.goto("/discover?mode=catalog");
  await expect(page.locator(".catalog-event")).toHaveCount(20);
}

test("default swipes, independent hearts, and filters retained across modes", async ({
  page,
}) => {
  const { saved } = await mockApp(page);
  await page.goto("/discover");
  await expect(page.locator(".swipe-card")).toBeVisible();
  await page.getByRole("button", { name: "Каталог", exact: true }).click();
  await expect(page.locator(".catalog-event")).toHaveCount(20);
  await expect(page.locator(".collection-tile")).toHaveCount(3);
  await page.locator(".catalog-heart").first().click();
  await expect(page.locator(".catalog-heart").first()).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(saved.has("1")).toBeTruthy();
  await expect(page).toHaveURL(/\/discover/);
  await page.getByRole("button", { name: "Бесплатно", exact: true }).click();
  await expect(page.locator(".catalog-event")).toHaveCount(9);
  await expect(page.locator(".catalog-collections")).toHaveCount(0);
  await page.getByRole("button", { name: "Свайпы", exact: true }).click();
  await page.getByRole("button", { name: "Каталог", exact: true }).click();
  await expect(page.locator(".catalog-event")).toHaveCount(9);
  await expect(
    page.getByRole("button", { name: "Бесплатно", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.locator(".catalog-heart").first().click();
  await expect(page.locator(".catalog-heart").first()).toHaveAttribute(
    "aria-pressed",
    "false",
  );
});

test("sheet applies date and budget, cancels drafts and restores focus", async ({
  page,
}) => {
  await mockApp(page);
  await openCatalog(page);
  const opener = page.getByRole("button", { name: "Фильтры", exact: true }),
    dialog = page.getByRole("dialog");
  await opener.click();
  await expect(dialog).toBeVisible();
  await page.getByLabel("Когда", { exact: true }).selectOption("date");
  await page.getByLabel("Дата события").fill("2026-10-03");
  await page.getByLabel("Стоимость", { exact: true }).selectOption("budget");
  await page.getByRole("button", { name: "1 000 ₽", exact: true }).click();
  await page.getByRole("button", { name: "Концерты", exact: true }).click();
  await page.getByRole("button", { name: "Применить", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(opener).toBeFocused();
  await expect(page).toHaveURL(/date_mode=date/);
  await expect(page).toHaveURL(/budget_max=1000/);
  await expect(page.locator(".catalog-event")).toHaveCount(12);
  await opener.click();
  await page.getByLabel("Когда", { exact: true }).selectOption("today");
  await page.keyboard.press("Escape");
  await expect(opener).toBeFocused();
  await expect(page).toHaveURL(/date_mode=date/);
  await opener.click();
  await page
    .getByRole("button", { name: "Сбросить", exact: true })
    .last()
    .click();
  await page.getByRole("button", { name: "Закрыть фильтры" }).click();
  await expect(page).toHaveURL(/budget_max=1000/);
  await opener.click();
  await page.keyboard.press("Shift+Tab");
  expect(
    await page.evaluate(() => !!document.activeElement?.closest("dialog")),
  ).toBeTruthy();
  await dialog.click({ position: { x: 5, y: 5 } });
  await expect(dialog).toHaveCount(0);
  await expect(opener).toBeFocused();
});

test("quick dates are exclusive; collection filters are editable and removable", async ({
  page,
}) => {
  await mockApp(page);
  await openCatalog(page);
  await page
    .getByRole("button", { name: "Бесплатно на выходных", exact: true })
    .click();
  await expect(page).toHaveURL(/date_mode=weekend/);
  await expect(page).toHaveURL(/free_only=true/);
  await page.getByRole("button", { name: "Сегодня", exact: true }).click();
  await expect(page).toHaveURL(/date_mode=today/);
  await page.getByRole("button", { name: "Сегодня", exact: true }).click();
  await expect(page).not.toHaveURL(/date_mode=/);
  await page.getByRole("button", { name: "Снять фильтр: Бесплатно" }).click();
  await expect(page.locator(".collection-tile")).toHaveCount(3);
  await page
    .getByRole("button", { name: "Вечер в городе", exact: true })
    .click();
  await expect(page).toHaveURL(/time=evening/);
  await page.getByRole("button", { name: "Сбросить", exact: true }).click();
  await page
    .getByRole("button", { name: "Выставки и прогулки", exact: true })
    .click();
  await expect(page).toHaveURL(/categories=ekskursii/);
  await expect(page).toHaveURL(/categories=vystavki/);
  await expect(page.locator(".catalog-event")).toHaveCount(13);
});

test("collection uses available categories and disappears without either", async ({
  page,
}) => {
  await mockApp(page, categories.slice(0, 2));
  await openCatalog(page);
  await page.getByRole("button", { name: "Выставки и прогулки" }).click();
  await expect(page).toHaveURL(/categories=vystavki/);
  await expect(page).not.toHaveURL(/ekskursii/);
  await page.unroute("**/api/v1/**");
  await mockApp(page, categories.slice(0, 1));
  await page.goto("/discover?mode=catalog");
  await expect(page.locator(".collection-tile")).toHaveCount(2);
});

test("search debounces and ignores old responses; clearing preserves filters", async ({
  page,
}) => {
  const { requests } = await mockApp(page);
  await openCatalog(page);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/events/catalog?*", async (route) => {
    if (new URL(route.request().url()).searchParams.get("q") === "Событие 2") {
      await gate;
      await route
        .fulfill({
          json: {
            items: [{ ...events[1], is_saved: false }],
            total: 1,
            has_more: false,
          },
        })
        .catch(() => {});
    } else await route.fallback();
  });
  const search = page.getByRole("textbox", {
    name: "Поиск события или площадки",
  });
  const oldRequest = page.waitForRequest(
    (request) => new URL(request.url()).searchParams.get("q") === "Событие 2",
  );
  await search.fill("Событие 2");
  await oldRequest;
  await search.fill("Событие 25");
  await expect(page.locator(".catalog-event h3")).toHaveText(["Событие 25"]);
  release();
  await expect(page.locator(".catalog-event h3")).toHaveText(["Событие 25"]);
  const before = requests.length;
  await search.fill("Г");
  await search.fill("Га");
  await search.fill("ГАЛЕРЕЯ");
  await expect(page.locator(".catalog-event")).toHaveCount(20);
  expect(requests.length).toBe(before + 1);
  await page.getByRole("button", { name: "Бесплатно", exact: true }).click();
  await page.getByRole("button", { name: "Очистить поиск" }).click();
  await expect(page).not.toHaveURL(/q=/);
  await expect(page).toHaveURL(/free_only=true/);
  await expect(page.locator(".catalog-event")).toHaveCount(9);
});

test("loaded pages, scroll and updated favorites survive details", async ({
  page,
}) => {
  const { requests } = await mockApp(page);
  await openCatalog(page);
  await page.getByRole("button", { name: "Показать ещё" }).click();
  await expect(page.locator(".catalog-event")).toHaveCount(25);
  const row = page.locator(".catalog-event").nth(22);
  await row.scrollIntoViewIfNeeded();
  const previousScroll = await page.evaluate(() => window.scrollY),
    count = requests.length;
  await row.getByRole("button", { name: /Подробнее/ }).click();
  await page.getByRole("button", { name: "Хочу пойти", exact: true }).click();
  await page.getByRole("button", { name: "Назад", exact: true }).click();
  await expect(page.locator(".catalog-event")).toHaveCount(25);
  await expect(page.locator(".catalog-heart").nth(22)).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(requests.length).toBe(count);
  await expect
    .poll(() => page.evaluate(() => window.scrollY))
    .toBeGreaterThan(previousScroll - 40);
});

test("save and pagination errors preserve results and permit retry", async ({
  page,
}) => {
  await mockApp(page);
  await openCatalog(page);
  await page.route("**/reaction", (route) =>
    route.fulfill({ status: 500, json: { detail: "Не удалось сохранить" } }),
  );
  await page.locator(".catalog-heart").first().click();
  await expect(page.locator(".catalog-heart").first()).toHaveAttribute(
    "aria-pressed",
    "false",
  );
  await expect(page.getByRole("alert")).toContainText("Не удалось сохранить");
  let fail = true;
  await page.route("**/events/catalog?*", async (route) => {
    if (new URL(route.request().url()).searchParams.has("offset") && fail) {
      fail = false;
      await route.fulfill({
        status: 500,
        json: { detail: "Ошибка следующей страницы" },
      });
    } else await route.fallback();
  });
  await page.getByRole("button", { name: "Показать ещё" }).click();
  await expect(page.getByText("Ошибка следующей страницы")).toBeVisible();
  await expect(page.locator(".catalog-event")).toHaveCount(20);
  await page
    .getByRole("button", { name: "Повторить загрузку", exact: true })
    .click();
  await expect(page.locator(".catalog-event")).toHaveCount(25);
});

test("initial errors and empty search offer retry or reset", async ({
  page,
}) => {
  await mockApp(page);
  let fail = true;
  await page.route("**/events/catalog?*", async (route) => {
    if (fail) {
      await route.fulfill({
        status: 502,
        json: { detail: "Источник недоступен" },
      });
    } else await route.fallback();
  });
  await page.goto("/discover?mode=catalog");
  await expect(page.getByRole("alert")).toContainText("Источник недоступен");
  fail = false;
  await page.getByRole("button", { name: "Повторить", exact: true }).click();
  await expect(page.locator(".catalog-event")).toHaveCount(20);
  await page
    .getByRole("textbox", { name: "Поиск события или площадки" })
    .fill("Неизвестное событие");
  await expect(
    page.getByRole("heading", { name: "По этим условиям событий пока нет" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Сбросить", exact: true })
    .last()
    .click();
  await expect(page.locator(".catalog-event")).toHaveCount(20);
});

for (const width of [360, 390, 520]) {
  test(`catalog and filter sheet fit ${width}px and keyboard-sized viewport`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 844 });
    await mockApp(page);
    await openCatalog(page);
    await expect(page.locator("body")).toHaveJSProperty("scrollWidth", width);
    await page.screenshot({ path: `test-results/catalog-${width}.png` });
    await page.getByRole("button", { name: "Фильтры", exact: true }).click();
    expect(
      (await page.locator(".filter-sheet").boundingBox())!.height,
    ).toBeLessThanOrEqual(844 * 0.85 + 1);
    await page.getByLabel("Стоимость", { exact: true }).selectOption("budget");
    await page.getByLabel("Максимальная цена входа, ₽").fill("1000");
    await page.screenshot({
      path: `test-results/catalog-filters-${width}.png`,
    });
    await page.setViewportSize({ width, height: 480 });
    await expect(page.locator(".sheet-footer")).toBeInViewport();
    await expect(page.locator("body")).toHaveJSProperty("scrollWidth", width);
    await page.getByRole("button", { name: "Применить", exact: true }).click();
    await expect(page).toHaveURL(/budget_max=1000/);
  });
}

test("a late next-page response cannot append cards after filters change", async ({
  page,
}) => {
  await mockApp(page);
  await openCatalog(page);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/events/catalog?*", async (route) => {
    if (new URL(route.request().url()).searchParams.has("offset")) {
      await gate;
      await route.fulfill({
        json: {
          items: events
            .slice(20)
            .map((event) => ({ ...event, is_saved: false })),
          total: 25,
          has_more: false,
        },
      });
    } else await route.fallback();
  });
  await page.getByRole("button", { name: "Показать ещё" }).click();
  await page.getByRole("button", { name: "Бесплатно", exact: true }).click();
  await expect(page.locator(".catalog-event")).toHaveCount(9);
  release();
  await expect(page.locator(".catalog-event")).toHaveCount(9);
  await expect(
    page.getByRole("heading", { name: "Ближайшие события · 9" }),
  ).toBeVisible();
});

test("category failures can be retried without losing catalog results", async ({
  page,
}) => {
  await mockApp(page);
  let fail = true;
  await page.route("**/categories", async (route) => {
    if (fail)
      await route.fulfill({
        status: 502,
        json: { detail: "Категории недоступны" },
      });
    else await route.fallback();
  });
  await openCatalog(page);
  await page.getByRole("button", { name: "Фильтры", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Категории недоступны");
  fail = false;
  await page
    .getByRole("button", { name: "Повторить загрузку категорий" })
    .click();
  await expect(
    page.getByRole("button", { name: "Концерты", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Закрыть фильтры" }).click();
  await expect(page.locator(".catalog-event")).toHaveCount(20);
  await expect(page.locator(".collection-tile")).toHaveCount(3);
});

test("clearing a pending search after snapshot restoration finishes loading", async ({
  page,
}) => {
  await mockApp(page);
  await openCatalog(page);
  await page.getByRole("button", { name: "Свайпы", exact: true }).click();
  await page.getByRole("button", { name: "Каталог", exact: true }).click();
  await expect(page.locator(".catalog-event")).toHaveCount(20);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/events/catalog?*", async (route) => {
    if (new URL(route.request().url()).searchParams.get("q") === "Ожидание") {
      await gate;
      await route
        .fulfill({ json: { items: [], total: 0, has_more: false } })
        .catch(() => {});
    } else await route.fallback();
  });
  const request = page.waitForRequest(
    (request) => new URL(request.url()).searchParams.get("q") === "Ожидание",
  );
  await page
    .getByRole("textbox", { name: "Поиск события или площадки" })
    .fill("Ожидание");
  await request;
  await expect(page.getByRole("status")).toContainText("Обновляем события");
  await page.getByRole("button", { name: "Очистить поиск" }).click();
  await expect(page.locator(".catalog-results")).toHaveAttribute(
    "aria-busy",
    "false",
  );
  release();
  await expect(page.locator(".catalog-event")).toHaveCount(20);
});
