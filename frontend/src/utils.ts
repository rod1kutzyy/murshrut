import type { Event } from "./types";
export const date = (e: Event) =>
  new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    timeZone: e.timezone,
  }).format(new Date(e.start_date));
export const time = (e: Event) =>
  new Intl.DateTimeFormat("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: e.timezone,
  }).format(new Date(e.start_date));
export const price = (e: Event) =>
  e.is_free
    ? "Бесплатно"
    : e.price_min == null
      ? "Цена уточняется"
      : `от ${e.price_min.toLocaleString("ru-RU")} ₽`;
export function deepLink(e: Event, bot: string) {
  return bot
    ? `https://max.ru/${encodeURIComponent(bot)}?startapp=event_${e.id}`
    : `${location.origin}/?startapp=event_${e.id}`;
}
export async function share(e: Event, bot: string) {
  const text = `🐱 Нашёл интересное мероприятие!\n\n${e.title}\n📅 ${date(e)} · ${time(e)}\n📍 ${e.city}, ${e.location_name}`;
  const link = deepLink(e, bot);
  if (window.WebApp?.initData && window.WebApp.shareMaxContent)
    await window.WebApp.shareMaxContent({ text, link });
  else if (navigator.share)
    await navigator.share({ title: e.title, text, url: link });
  else {
    await navigator.clipboard.writeText(`${text}\n${link}`);
    return "Ссылка скопирована";
  }
  return "Готово";
}
