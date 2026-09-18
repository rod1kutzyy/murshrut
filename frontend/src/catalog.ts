export type CatalogFilters = {
  q: string;
  date_mode: "any" | "today" | "weekend" | "date";
  date: string;
  categories: string[];
  free_only: boolean;
  budget_max: number | null;
  time: "any" | "evening";
};

export const emptyFilters = (): CatalogFilters => ({
  q: "",
  date_mode: "any",
  date: "",
  categories: [],
  free_only: false,
  budget_max: null,
  time: "any",
});

export function readFilters(params: URLSearchParams): CatalogFilters {
  const modes = ["any", "today", "weekend", "date"];
  let date_mode = params.get("date_mode") || "any";
  if (!modes.includes(date_mode)) date_mode = "any";
  let date = params.get("date") || "";
  const parsed = new Date(`${date}T12:00:00Z`);
  if (
    !/^\d{4}-\d{2}-\d{2}$/.test(date) ||
    Number.isNaN(parsed.getTime()) ||
    parsed.toISOString().slice(0, 10) !== date
  ) {
    date = "";
    if (date_mode === "date") date_mode = "any";
  }
  const free_only = params.get("free_only") === "true";
  const budget = params.has("budget_max")
    ? Number(params.get("budget_max"))
    : NaN;
  return {
    q: (params.get("q") || "").trim().slice(0, 200),
    date_mode: date_mode as CatalogFilters["date_mode"],
    date,
    categories: [...new Set(params.getAll("categories").filter(Boolean))],
    free_only,
    budget_max:
      !free_only && Number.isInteger(budget) && budget >= 0 && budget <= 1000000
        ? budget
        : null,
    time: params.get("time") === "evening" ? "evening" : "any",
  };
}

export function filterParams(filters: CatalogFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.q.trim()) params.set("q", filters.q.trim());
  if (filters.date_mode !== "any") params.set("date_mode", filters.date_mode);
  if (filters.date_mode === "date") params.set("date", filters.date);
  [...filters.categories]
    .sort()
    .forEach((id) => params.append("categories", id));
  if (filters.free_only) params.set("free_only", "true");
  else if (filters.budget_max !== null)
    params.set("budget_max", String(filters.budget_max));
  if (filters.time !== "any") params.set("time", filters.time);
  return params;
}

export const COLLECTIONS = [
  {
    id: "free-weekend",
    title: "Бесплатно на выходных",
    icon: "sun",
    filters: { date_mode: "weekend", free_only: true },
  },
  {
    id: "evening",
    title: "Вечер в городе",
    icon: "moon",
    filters: { time: "evening" },
  },
  {
    id: "art-walk",
    title: "Выставки и прогулки",
    icon: "palette",
    filters: { categories: ["vystavki", "ekskursii"] },
  },
] satisfies {
  id: string;
  title: string;
  icon: string;
  filters: Partial<CatalogFilters>;
}[];
