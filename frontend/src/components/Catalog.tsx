import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Moon, Palette, Search, SlidersHorizontal, Sun, X } from "lucide-react";
import type { CatalogResult, Category, Event, User } from "../types";
import { api } from "../api";
import {
  COLLECTIONS,
  emptyFilters,
  filterParams,
  readFilters,
  type CatalogFilters,
} from "../catalog";
import { ErrorMessage, State } from "./State";
import CatalogFilterSheet from "./CatalogFilters";
import CatalogEventRow from "./CatalogEventRow";

// Session-only snapshots retain loaded pages when returning from event details.
const snapshots = new Map<string, { data: CatalogResult; scroll: number }>();
const MAX_SNAPSHOTS = 20;
function remember(key: string, data: CatalogResult, scroll: number) {
  snapshots.delete(key);
  snapshots.set(key, { data, scroll });
  if (snapshots.size > MAX_SNAPSHOTS)
    snapshots.delete(snapshots.keys().next().value!);
}

export default function Catalog({ user }: { user: User }) {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const filters = readFilters(params);
  const query = filterParams(filters).toString();
  const key = `${user.id}:${user.city}:${query}`;
  const initial = useRef(snapshots.get(key));
  const initialKey = useRef(key);
  const restoreAllowed = useRef(true);
  const currentKey = useRef(key);
  currentKey.current = key;
  const latestFilters = useRef(filters);
  latestFilters.current = filters;
  const generation = useRef(0);
  const [view, setView] = useState<{ key: string; data: CatalogResult | null }>(
    { key, data: initial.current?.data || null },
  );
  const data = view.key === key ? view.data : null;
  const [loading, setLoading] = useState(!initial.current);
  const displayed = data || (loading ? view.data : null);
  const [moreLoading, setMoreLoading] = useState(false);
  const [error, setError] = useState("");
  const [moreError, setMoreError] = useState("");
  const [retry, setRetry] = useState(0);
  const [input, setInput] = useState(filters.q);
  const [categories, setCategories] = useState<Category[]>([]);
  const [categoryError, setCategoryError] = useState("");
  const [categoryLoading, setCategoryLoading] = useState(true);
  const [categoryRetry, setCategoryRetry] = useState(0);
  const [sheet, setSheet] = useState(false);
  const [saveErrors, setSaveErrors] = useState<Record<string, string>>({});
  const [pending, setPending] = useState<Set<string>>(new Set());
  const locked = useRef(new Set<string>());
  const savedOverrides = useRef(new Map<string, boolean>());
  const results = useRef<HTMLDivElement>(null);
  const scrollToResults = useRef(false);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  function apply(next: CatalogFilters) {
    setInput(next.q);
    const nextParams = filterParams(next);
    nextParams.set("mode", "catalog");
    setParams(nextParams, { replace: true });
  }
  useEffect(() => {
    setInput(filters.q);
  }, [filters.q]);
  useEffect(() => {
    if (input.trim() === filters.q) return;
    const timer = window.setTimeout(() => {
      const next = filterParams({ ...latestFilters.current, q: input.trim() });
      next.set("mode", "catalog");
      setParams(next, { replace: true });
    }, 300);
    return () => window.clearTimeout(timer);
  }, [input, filters.q, setParams]);

  useEffect(() => {
    const controller = new AbortController();
    setCategoryError("");
    setCategoryLoading(true);
    api<Category[]>("/categories", { signal: controller.signal })
      .then((response) => {
        if (!controller.signal.aborted) setCategories(response);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setCategoryError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setCategoryLoading(false);
      });
    return () => controller.abort();
  }, [categoryRetry]);

  useEffect(() => {
    const controller = new AbortController();
    const version = ++generation.current;
    setError("");
    setMoreError("");
    setMoreLoading(false);
    if (key !== initialKey.current) restoreAllowed.current = false;
    if (
      restoreAllowed.current &&
      initial.current &&
      view.key === key &&
      view.data &&
      retry === 0
    ) {
      setLoading(false);
      // Details and swipes may have changed favorites since the snapshot was saved.
      api<Event[]>("/events/favorites", { signal: controller.signal })
        .then((events) => {
          if (controller.signal.aborted) return;
          const ids = new Set(events.map((event) => event.id));
          setView((current) =>
            current.key !== key || !current.data
              ? current
              : {
                  key,
                  data: {
                    ...current.data,
                    items: current.data.items.map((event) => ({
                      ...event,
                      is_saved:
                        savedOverrides.current.get(event.id) ??
                        ids.has(event.id),
                    })),
                  },
                },
          );
        })
        .catch((e) => {
          if (!controller.signal.aborted)
            setError(`Не удалось обновить избранное. ${e.message}`);
        });
      return () => {
        controller.abort();
        generation.current++;
      };
    }
    setLoading(true);
    api<CatalogResult>(`/events/catalog?${query}`, {
      signal: controller.signal,
    })
      .then((response) => {
        if (controller.signal.aborted || generation.current !== version) return;
        setView({
          key,
          data: {
            ...response,
            items: response.items.map((event) => ({
              ...event,
              is_saved: savedOverrides.current.get(event.id) ?? event.is_saved,
            })),
          },
        });
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => {
      controller.abort();
      generation.current++;
    };
  }, [key, query, retry]);

  useEffect(() => {
    if (data) remember(key, data, snapshots.get(key)?.scroll || 0);
  }, [key, data]);
  useEffect(() => {
    function captureScroll() {
      const snapshot = snapshots.get(currentKey.current);
      if (snapshot) snapshot.scroll = window.scrollY;
    }
    window.addEventListener("scroll", captureScroll, { passive: true });
    return () => window.removeEventListener("scroll", captureScroll);
  }, []);
  useLayoutEffect(() => {
    if (!initial.current) return;
    const scroll = initial.current.scroll;
    window.scrollTo(0, scroll);
    const frame = requestAnimationFrame(() => window.scrollTo(0, scroll));
    return () => cancelAnimationFrame(frame);
  }, []);
  useEffect(() => {
    if (!loading && data && scrollToResults.current) {
      scrollToResults.current = false;
      results.current?.scrollIntoView({
        block: "start",
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "instant"
          : "smooth",
      });
    }
  }, [loading, data]);

  async function loadMore() {
    if (!data || moreLoading || loading) return;
    const version = generation.current;
    setMoreLoading(true);
    setMoreError("");
    const next = new URLSearchParams(query);
    next.set("offset", String(data.items.length));
    try {
      const response = await api<CatalogResult>(`/events/catalog?${next}`);
      if (!alive.current || generation.current !== version) return;
      setView((current) => {
        if (current.key !== key || !current.data) return current;
        const ids = new Set(current.data.items.map((event) => event.id));
        return {
          key,
          data: {
            ...response,
            items: [
              ...current.data.items,
              ...response.items
                .filter((event) => !ids.has(event.id))
                .map((event) => ({
                  ...event,
                  is_saved:
                    savedOverrides.current.get(event.id) ?? event.is_saved,
                })),
            ],
          },
        };
      });
    } catch (e) {
      if (alive.current && generation.current === version)
        setMoreError((e as Error).message);
    } finally {
      if (alive.current && generation.current === version)
        setMoreLoading(false);
    }
  }
  async function save(event: CatalogResult["items"][number]) {
    if (locked.current.has(event.id)) return;
    locked.current.add(event.id);
    setPending(new Set(locked.current));
    setSaveErrors((current) => ({ ...current, [event.id]: "" }));
    try {
      await api(
        `/events/${event.id}/reaction`,
        event.is_saved
          ? { method: "DELETE" }
          : { method: "POST", body: JSON.stringify({ reaction: "like" }) },
      );
      savedOverrides.current.set(event.id, !event.is_saved);
      // Keep all retained catalog pages consistent with the successful reaction.
      for (const [snapshotKey, snapshot] of snapshots) {
        if (snapshotKey.startsWith(`${user.id}:`))
          snapshot.data = {
            ...snapshot.data,
            items: snapshot.data.items.map((item) =>
              item.id === event.id
                ? { ...item, is_saved: !event.is_saved }
                : item,
            ),
          };
      }
      if (!alive.current) return;
      setView((current) =>
        !current.data
          ? current
          : {
              ...current,
              data: {
                ...current.data,
                items: current.data.items.map((item) =>
                  item.id === event.id
                    ? { ...item, is_saved: !event.is_saved }
                    : item,
                ),
              },
            },
      );
    } catch (e) {
      if (alive.current)
        setSaveErrors((current) => ({
          ...current,
          [event.id]: (e as Error).message,
        }));
    } finally {
      locked.current.delete(event.id);
      if (alive.current) setPending(new Set(locked.current));
    }
  }
  function openEvent(id: string) {
    if (data) remember(key, data, window.scrollY);
    navigate(`/events/${id}`);
  }
  const active = query.length > 0;
  const pills: { id: string; label: string; remove: () => void }[] = [];
  if (filters.q)
    pills.push({
      id: "q",
      label: `«${filters.q}»`,
      remove: () => apply({ ...filters, q: "" }),
    });
  if (filters.date_mode !== "any")
    pills.push({
      id: "date",
      label:
        filters.date_mode === "today"
          ? "Сегодня"
          : filters.date_mode === "weekend"
            ? "Выходные"
            : new Intl.DateTimeFormat("ru-RU", {
                day: "numeric",
                month: "long",
                timeZone: "UTC",
              }).format(new Date(`${filters.date}T12:00:00Z`)),
      remove: () => apply({ ...filters, date_mode: "any", date: "" }),
    });
  if (filters.free_only || filters.budget_max !== null)
    pills.push({
      id: "cost",
      label: filters.free_only
        ? "Бесплатно"
        : `До ${filters.budget_max!.toLocaleString("ru-RU")} ₽`,
      remove: () => apply({ ...filters, free_only: false, budget_max: null }),
    });
  if (filters.time === "evening")
    pills.push({
      id: "time",
      label: "Вечером",
      remove: () => apply({ ...filters, time: "any" }),
    });
  filters.categories.forEach((id) =>
    pills.push({
      id: `category-${id}`,
      label: categories.find((category) => category.id === id)?.name || id,
      remove: () =>
        apply({
          ...filters,
          categories: filters.categories.filter((category) => category !== id),
        }),
    }),
  );

  return (
    <div className="catalog">
      <div className="catalog-search">
        <Search size={18} />
        <input
          aria-label="Поиск события или площадки"
          placeholder="Событие или площадка"
          maxLength={200}
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        {input && (
          <button
            aria-label="Очистить поиск"
            onClick={() => apply({ ...filters, q: "" })}
          >
            <X size={18} />
          </button>
        )}
      </div>
      <div className="catalog-quick-filters">
        {(["today", "weekend"] as const).map((mode) => (
          <button
            className={`chip ${filters.date_mode === mode ? "selected" : ""}`}
            key={mode}
            aria-pressed={filters.date_mode === mode}
            onClick={() =>
              apply({
                ...filters,
                q: input.trim(),
                date_mode: filters.date_mode === mode ? "any" : mode,
                date: "",
              })
            }
          >
            {mode === "today" ? "Сегодня" : "Выходные"}
          </button>
        ))}
        <button
          className={`chip ${filters.free_only ? "selected" : ""}`}
          aria-pressed={filters.free_only}
          onClick={() =>
            apply({
              ...filters,
              q: input.trim(),
              free_only: !filters.free_only,
              budget_max: null,
            })
          }
        >
          Бесплатно
        </button>
        <button className="chip filter-trigger" onClick={() => setSheet(true)}>
          <SlidersHorizontal size={16} />
          Фильтры
        </button>
      </div>
      {active || input.trim() ? (
        <div className="catalog-applied">
          <div className="chips">
            {pills.map((pill) => (
              <button
                className="chip selected"
                key={pill.id}
                aria-label={`Снять фильтр: ${pill.label}`}
                onClick={pill.remove}
              >
                {pill.label}
                <X size={14} />
              </button>
            ))}
          </div>
          <button
            className="text-button catalog-reset"
            onClick={() => apply(emptyFilters())}
          >
            Сбросить
          </button>
        </div>
      ) : (
        <div className="catalog-collections">
          <h2>Под настроение</h2>
          <div className="collection-tiles">
            {COLLECTIONS.map((collection) => {
              const available =
                "categories" in collection.filters
                  ? (collection.filters.categories || []).filter((id) =>
                      categories.some((category) => category.id === id),
                    )
                  : [];
              if ("categories" in collection.filters && !available.length)
                return null;
              const Icon =
                collection.icon === "sun"
                  ? Sun
                  : collection.icon === "moon"
                    ? Moon
                    : Palette;
              return (
                <button
                  key={collection.id}
                  className={`collection-tile ${collection.id}`}
                  onClick={() => {
                    scrollToResults.current = true;
                    apply({
                      ...emptyFilters(),
                      ...collection.filters,
                      ...("categories" in collection.filters
                        ? { categories: available }
                        : {}),
                    });
                  }}
                >
                  <Icon size={21} />
                  <span>{collection.title}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}
      <div
        className="catalog-results"
        ref={results}
        aria-busy={loading || moreLoading}
      >
        <h2>Ближайшие события{data ? ` · ${data.total}` : ""}</h2>
        {loading && !displayed ? (
          <div
            className="catalog-skeletons"
            role="status"
            aria-label="Загружаем события"
          >
            {[1, 2, 3].map((id) => (
              <div className="catalog-skeleton" key={id}>
                <div />
                <div>
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <>
            {loading && (
              <p className="catalog-loading" role="status">
                Обновляем события…
              </p>
            )}
            {error && (
              <>
                <ErrorMessage message={error} />
                <button
                  className="catalog-secondary"
                  onClick={() => setRetry((value) => value + 1)}
                >
                  Повторить
                </button>
              </>
            )}
            {data && !loading && !data.items.length && !error && (
              <State
                title={
                  active
                    ? "По этим условиям событий пока нет"
                    : "В городе пока нет событий"
                }
                text={
                  active
                    ? "Попробуйте другую дату или уберите часть фильтров."
                    : "Можно выбрать другой город или вернуться позже."
                }
                label={active ? "Сбросить" : "Выбрать город"}
                action={() =>
                  active ? apply(emptyFilters()) : navigate("/profile")
                }
              />
            )}
            {displayed && (
              <div className="catalog-event-list">
                {displayed.items.map((event) => (
                  <CatalogEventRow
                    key={event.id}
                    event={event}
                    busy={pending.has(event.id) || loading}
                    error={saveErrors[event.id] || ""}
                    onOpen={() => openEvent(event.id)}
                    onSave={() => save(event)}
                  />
                ))}
              </div>
            )}
            <ErrorMessage message={moreError} />
            {data?.has_more && (
              <button
                className="catalog-secondary catalog-more"
                disabled={moreLoading || loading}
                onClick={loadMore}
              >
                {moreLoading
                  ? "Загружаем…"
                  : moreError
                    ? "Повторить загрузку"
                    : "Показать ещё"}
              </button>
            )}
          </>
        )}
      </div>
      {sheet && (
        <CatalogFilterSheet
          filters={filters}
          categories={categories}
          categoryError={categoryError}
          categoryLoading={categoryLoading}
          retryCategories={() => setCategoryRetry((value) => value + 1)}
          onClose={() => setSheet(false)}
          onApply={(next) => {
            apply({ ...next, q: input.trim() });
            setSheet(false);
          }}
        />
      )}
    </div>
  );
}
