import { test, expect } from "@playwright/test";

test("mobile preferences, like, swipe, details, map and deep link", async ({
  page,
  request,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  // External bridge and map tiles are not needed to test the application flow.
  await page.route("https://st.max.ru/**", (route) =>
    route.fulfill({ body: "" }),
  );
  await page.goto("/");
  await expect(page.locator(".app-shell, .onboarding")).toBeVisible();
  if (await page.getByText("Знакомство · 1 / 3").isVisible()) {
    await page.getByRole("button", { name: /Продолжить/ }).click();
    await page.getByRole("button", { name: /Продолжить/ }).click();
    await page.getByRole("button", { name: /Найти мои события/ }).click();
  } else {
    await page.getByRole("link", { name: "Мой вкус" }).click();
    await expect(page.getByLabel("В каком городе ищем?")).toBeVisible();
    await page.getByLabel("В каком городе ищем?").selectOption("Москва");
    await page.getByRole("button", { name: /Сохранить предпочтения/ }).click();
    await page.getByRole("link", { name: "Открывать" }).click();
  }
  await expect(page.locator(".swipe-card")).toBeVisible();
  await expect(page.locator("body")).toHaveJSProperty("scrollWidth", 390);
  const reaction = await page
    .getByRole("button", { name: "Нравится", exact: true })
    .boundingBox();
  const nav = await page.locator(".bottom-nav").boundingBox();
  expect(
    reaction && nav && reaction.y + reaction.height <= nav.y,
    JSON.stringify({ reaction, nav }),
  ).toBeTruthy();
  await page.screenshot({ path: "test-results/discover.png", fullPage: true });
  const title = await page.locator(".swipe-card h2").innerText();
  await page.getByRole("button", { name: "Нравится", exact: true }).click();
  await expect(page.locator(".swipe-card h2")).not.toHaveText(title);
  await page.getByRole("link", { name: "Мои события" }).click();
  await expect(
    page.getByRole("heading", { name: title, exact: true }),
  ).toBeVisible();
  await page.locator(".event-list-item").filter({ hasText: title }).click();
  await expect(
    page.getByRole("heading", { name: "Где встречаемся" }),
  ).toBeVisible();
  await expect(page.locator(".event-map")).toBeVisible();
  const eventId = page.url().split("/events/")[1];
  await page.screenshot({ path: "test-results/details.png", fullPage: true });
  await page.evaluate(() => {
    window.WebApp = {
      initData: "test-launch",
      shareMaxContent: (params) => {
        sessionStorage.setItem("shared", JSON.stringify(params));
      },
    };
  });
  await page
    .getByRole("button", { name: "Поделиться", exact: true })
    .last()
    .click();
  const shared = await page.evaluate(() =>
    JSON.parse(sessionStorage.getItem("shared") || "{}"),
  );
  expect(shared.text).toContain(title);
  expect(shared.link).toContain(`startapp=event_${eventId}`);
  await page.goto(`/?startapp=event_${eventId}`);
  await expect(
    page.getByRole("heading", { name: title, exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Убрать из моих событий/ }).click();
  await expect(page.getByRole("button", { name: "Хочу пойти" })).toBeVisible();
  await page.getByRole("link", { name: "Открывать" }).click();
  await expect(page.locator(".swipe-card")).toBeVisible();
  const skipped = await page.locator(".swipe-card h2").innerText();
  const card = await page.locator(".hero-image").boundingBox();
  if (!card) throw new Error("No swipe card");
  await page.mouse.move(card.x + card.width / 2, card.y + 100);
  await page.mouse.down();
  await page.mouse.move(card.x + card.width / 2 - 125, card.y + 102, {
    steps: 8,
  });
  const reactionRequest = page.waitForRequest(
    (r) => r.method() === "POST" && r.url().endsWith("/reaction"),
  );
  await page.mouse.up();
  const skippedId = (await reactionRequest)
    .url()
    .split("/events/")[1]
    .split("/")[0];
  await expect(page.locator(".swipe-card h2")).not.toHaveText(skipped);
  await page.getByRole("button", { name: "Каталог", exact: true }).click();
  const skippedRow = page
    .locator(".catalog-event")
    .filter({ hasText: skipped });
  await expect(skippedRow).toBeVisible();
  await skippedRow.locator(".catalog-heart").click();
  await expect(skippedRow.locator(".catalog-heart")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  // Existing rows can still be visible while the filtered catalog is loading.
  const freeCatalogResponse = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return (
      url.pathname === "/api/v1/events/catalog" &&
      url.searchParams.get("free_only") === "true"
    );
  });
  await page.getByRole("button", { name: "Бесплатно", exact: true }).click();
  expect((await freeCatalogResponse).status()).toBe(200);
  await expect(page.locator(".catalog-results")).toHaveAttribute(
    "aria-busy",
    "false",
  );
  await expect(page.locator(".catalog-event .list-price").first()).toHaveText(
    "Бесплатно",
  );
  await page.getByRole("link", { name: "Карта", exact: true }).click();
  await page.getByRole("button", { name: "Для меня" }).click();
  await expect(page.locator(".event-map")).toBeVisible();
  await page.getByRole("link", { name: "Мой вкус" }).click();
  await page.getByLabel("В каком городе ищем?").selectOption("Казань");
  await page.getByRole("button", { name: /Сохранить предпочтения/ }).click();
  await expect(page.locator(".city-link")).toContainText("Казань");
  expect(errors).toEqual([]);
  // Restore the default city and reactions created by this test.
  const auth = await (await request.post("/api/v1/auth/demo")).json();
  const headers = { Authorization: `Bearer ${auth.access_token}` };
  await request.put("/api/v1/users/me/preferences", {
    headers,
    data: {
      city: "Москва",
      categories: ["koncerty", "vystavki"],
      budget_max: 1500,
    },
  });
  for (const id of [eventId, skippedId]) {
    await request.delete(`/api/v1/events/${id}/reaction`, { headers });
  }
});
