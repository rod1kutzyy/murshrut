import type { EveningOptions, EveningPlan } from "./types";

// Match the API exclusion limit; never discard previously shown variants.
export const EVENING_VARIANT_LIMIT = 200;

export const VIBES = [
  { value: "active", label: "Хочу движ", hint: "Музыка, встречи и энергия" },
  { value: "calm", label: "Спокойный вечер", hint: "Без спешки и суеты" },
  {
    value: "date",
    label: "Свидание",
    hint: "Впечатления, которые хочется разделить",
  },
  {
    value: "learn",
    label: "Хочу узнать что-то новое",
    hint: "Открытия и новые идеи",
  },
  {
    value: "culture",
    label: "Культурный вечер",
    hint: "Искусство, театр и музыка",
  },
  { value: "surprise", label: "Удиви меня", hint: "Доверьте выбор Муру" },
] as const;
export const DURATIONS = [
  { value: 2, label: "1–2 часа" },
  { value: 4, label: "3–4 часа" },
  { value: 6, label: "Весь вечер" },
] as const;
export const BUDGETS = [
  { value: 0, label: "Бесплатно" },
  { value: 1000, label: "До 1000 ₽" },
  { value: 3000, label: "До 3000 ₽" },
  { value: null, label: "Без ограничений" },
] as const;
export const eveningDate = (plan: EveningPlan) =>
  new Intl.DateTimeFormat("ru-RU", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: "UTC",
  }).format(new Date(`${plan.date}T12:00:00Z`));
export const eveningCost = (plan: EveningPlan) => {
  if (!plan.cost_complete)
    return `≈ ${plan.total_cost.toLocaleString("ru-RU")} ₽ + цена уточняется`;
  if (plan.events.every((event) => event.is_free)) return "Бесплатно";
  return `≈ ${plan.total_cost.toLocaleString("ru-RU")} ₽`;
};
export const eveningDuration = (minutes: number) => {
  const hours = Math.floor(minutes / 60),
    rest = minutes % 60;
  return [hours ? `${hours} ч` : "", rest ? `${rest} мин` : ""]
    .filter(Boolean)
    .join(" ");
};
export type EveningDraft = {
  options: Partial<EveningOptions>;
  step: number;
  plan: EveningPlan | null;
  shownIds: string[];
};
let owner = "";
let draft: EveningDraft | null = null;
export function setEveningOwner(key: string) {
  if (owner !== key) {
    owner = key;
    draft = null;
  }
}
export function getEveningDraft(key: string): EveningDraft {
  setEveningOwner(key);
  return draft || { options: {}, step: 0, plan: null, shownIds: [] };
}
export function rememberEveningDraft(key: string, value: EveningDraft) {
  if (key === owner) draft = value;
}
