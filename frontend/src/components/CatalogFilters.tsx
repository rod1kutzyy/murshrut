import { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import type { Category } from "../types";
import { emptyFilters, type CatalogFilters } from "../catalog";

export default function CatalogFilterSheet({
  filters,
  categories,
  categoryError,
  categoryLoading,
  retryCategories,
  onApply,
  onClose,
}: {
  filters: CatalogFilters;
  categories: Category[];
  categoryError: string;
  categoryLoading: boolean;
  retryCategories: () => void;
  onApply: (filters: CatalogFilters) => void;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [draft, setDraft] = useState<CatalogFilters>({
    ...filters,
    categories: [...filters.categories],
  });
  const [cost, setCost] = useState(
    filters.free_only ? "free" : filters.budget_max !== null ? "budget" : "any",
  );
  const [budget, setBudget] = useState(
    filters.budget_max !== null ? String(filters.budget_max) : "",
  );
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    const node = dialog.current!;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    node.showModal();
    return () => {
      node.close();
      document.body.style.overflow = overflow;
      opener?.focus({ preventScroll: true });
    };
  }, []);
  function reset() {
    setDraft({ ...emptyFilters(), q: filters.q });
    setCost("any");
    setBudget("");
  }
  return (
    <dialog
      ref={dialog}
      className="filter-backdrop"
      aria-labelledby="filter-title"
      onKeyDown={(e) => {
        if (e.key !== "Tab") return;
        const controls = [
          ...e.currentTarget.querySelectorAll<HTMLElement>(
            "button:not([disabled]), input:not([disabled]), select:not([disabled])",
          ),
        ].filter((node) => node.getClientRects().length > 0);
        const first = controls[0],
          last = controls[controls.length - 1];
        if (
          e.shiftKey &&
          (document.activeElement === first ||
            !e.currentTarget.contains(document.activeElement))
        ) {
          e.preventDefault();
          last?.focus();
        } else if (
          !e.shiftKey &&
          (document.activeElement === last ||
            !e.currentTarget.contains(document.activeElement))
        ) {
          e.preventDefault();
          first?.focus();
        }
      }}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <form
        className="filter-sheet"
        onSubmit={(e) => {
          e.preventDefault();
          onApply({
            ...draft,
            free_only: cost === "free",
            budget_max: cost === "budget" ? Number(budget) : null,
          });
        }}
      >
        <div className="sheet-heading">
          <h2 id="filter-title">Фильтры</h2>
          <button
            type="button"
            className="icon-button"
            aria-label="Закрыть фильтры"
            onClick={onClose}
          >
            <X size={22} />
          </button>
        </div>
        <div className="sheet-fields">
          <div className="form-section">
            <label htmlFor="catalog-date-mode">Когда</label>
            <select
              id="catalog-date-mode"
              value={draft.date_mode}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  date_mode: e.target.value as CatalogFilters["date_mode"],
                })
              }
            >
              <option value="any">Любая дата</option>
              <option value="today">Сегодня</option>
              <option value="weekend">Выходные</option>
              <option value="date">Конкретная дата</option>
            </select>
            {draft.date_mode === "date" && (
              <>
                <label htmlFor="catalog-date">Дата события</label>
                <input
                  id="catalog-date"
                  type="date"
                  required
                  value={draft.date}
                  onChange={(e) => setDraft({ ...draft, date: e.target.value })}
                />
              </>
            )}
          </div>
          <fieldset className="form-section category-field">
            <legend>Категории</legend>
            {categoryError ? (
              <div role="alert">
                {categoryError}
                <button
                  type="button"
                  className="text-button"
                  onClick={retryCategories}
                >
                  Повторить загрузку категорий
                </button>
              </div>
            ) : !categories.length ? (
              <p className="subtitle">
                {categoryLoading
                  ? "Загружаем категории…"
                  : "В этом источнике пока нет категорий."}
              </p>
            ) : (
              <div className="chips">
                {categories.map((category) => (
                  <button
                    type="button"
                    key={category.id}
                    className={`chip ${draft.categories.includes(category.id) ? "selected" : ""}`}
                    aria-pressed={draft.categories.includes(category.id)}
                    onClick={() =>
                      setDraft({
                        ...draft,
                        categories: draft.categories.includes(category.id)
                          ? draft.categories.filter((id) => id !== category.id)
                          : [...draft.categories, category.id],
                      })
                    }
                  >
                    {category.name}
                  </button>
                ))}
              </div>
            )}
          </fieldset>
          <div className="form-section">
            <label htmlFor="catalog-cost">Стоимость</label>
            <select
              id="catalog-cost"
              value={cost}
              onChange={(e) => setCost(e.target.value)}
            >
              <option value="any">Любая стоимость</option>
              <option value="free">Бесплатно</option>
              <option value="budget">Бюджет до…</option>
            </select>
            {cost === "budget" && (
              <>
                <label htmlFor="catalog-budget">
                  Максимальная цена входа, ₽
                </label>
                <input
                  id="catalog-budget"
                  type="number"
                  inputMode="numeric"
                  min="0"
                  max="1000000"
                  step="1"
                  required
                  placeholder="Например, 1000"
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                />
                <div className="chips budget-suggestions">
                  {[500, 1000, 1500, 3000].map((amount) => (
                    <button
                      type="button"
                      className={`chip ${budget === String(amount) ? "selected" : ""}`}
                      key={amount}
                      onClick={() => setBudget(String(amount))}
                    >
                      {amount.toLocaleString("ru-RU")} ₽
                    </button>
                  ))}
                </div>
              </>
            )}
            <label htmlFor="catalog-time">Время</label>
            <select
              id="catalog-time"
              value={draft.time}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  time: e.target.value as CatalogFilters["time"],
                })
              }
            >
              <option value="any">Любое время</option>
              <option value="evening">Вечером — с 18:00</option>
            </select>
          </div>
        </div>
        <div className="sheet-footer">
          <button type="button" className="catalog-secondary" onClick={reset}>
            Сбросить
          </button>
          <button type="submit" className="catalog-primary">
            Применить
          </button>
        </div>
      </form>
    </dialog>
  );
}
