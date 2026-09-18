import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Heart,
  RefreshCw,
  Check,
  Sparkles,
} from "lucide-react";
import { api } from "../api";
import type {
  EveningGeneration,
  EveningOptions,
  EveningPlan,
  User,
} from "../types";
import {
  BUDGETS,
  EVENING_VARIANT_LIMIT,
  DURATIONS,
  VIBES,
  getEveningDraft,
  rememberEveningDraft,
} from "../evening";
import EveningRoute from "../components/EveningRoute";
import { ErrorMessage, State } from "../components/State";

export default function EveningPage({ user }: { user: User }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const ownerKey = `${user.id}:${user.city}`;
  const [draft, setDraft] = useState(() => getEveningDraft(ownerKey));
  const [savedPlan, setSavedPlan] = useState<EveningPlan | null>(null);
  const [loading, setLoading] = useState(!!id);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [empty, setEmpty] = useState(false);
  const [retry, setRetry] = useState(0);
  const locked = useRef(false);
  const active = useRef(true);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);
  useEffect(() => {
    if (!id) rememberEveningDraft(ownerKey, draft);
  }, [id, ownerKey, draft]);
  useEffect(() => {
    if (!id) return;
    let current = true;
    setLoading(true);
    setError("");
    setSavedPlan(null);
    api<EveningPlan>(`/evenings/${id}`)
      .then((plan) => {
        if (current) setSavedPlan(plan);
      })
      .catch((e) => {
        if (current) setError(e.message);
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => {
      current = false;
    };
  }, [id, retry]);
  const plan = id ? savedPlan : draft.plan;
  function select<K extends keyof EveningOptions>(
    key: K,
    value: EveningOptions[K],
  ) {
    setDraft((previous) => ({
      ...previous,
      options: { ...previous.options, [key]: value },
    }));
  }
  async function generate() {
    if (
      locked.current ||
      draft.options.vibe === undefined ||
      draft.options.duration_hours === undefined ||
      draft.options.budget_max === undefined
    )
      return;
    if (draft.shownIds.length >= EVENING_VARIANT_LIMIT) {
      setNotice(
        `Показано ${EVENING_VARIANT_LIMIT} вариантов с этими условиями. Измените условия, чтобы собрать новый вечер.`,
      );
      return;
    }
    locked.current = true;
    setBusy(true);
    setError("");
    setNotice("");
    setEmpty(false);
    try {
      const result = await api<EveningGeneration>("/evenings/generate", {
        method: "POST",
        body: JSON.stringify({
          ...draft.options,
          excluded_plan_ids: draft.shownIds,
        }),
      });
      if (!active.current) return;
      if (result.plan) {
        setDraft((previous) => ({
          ...previous,
          plan: result.plan,
          shownIds: [...previous.shownIds, result.plan!.id],
        }));
      } else if (plan) {
        setNotice(
          result.reason === "exhausted"
            ? "Другие варианты с этими условиями закончились. Попробуйте изменить условия."
            : "Новый маршрут пока не нашёлся. Попробуйте изменить условия.",
        );
      } else setEmpty(true);
    } catch (e) {
      if (active.current) setError((e as Error).message);
    } finally {
      locked.current = false;
      if (active.current) setBusy(false);
    }
  }
  async function save() {
    if (!plan || plan.saved || locked.current) return;
    locked.current = true;
    setBusy(true);
    setError("");
    try {
      const saved = await api<EveningPlan>(`/evenings/${plan.id}/save`, {
        method: "POST",
      });
      if (!active.current) return;
      if (id) setSavedPlan(saved);
      else setDraft((previous) => ({ ...previous, plan: saved }));
      setNotice("Вечер сохранён в «Мои события».");
    } catch (e) {
      if (active.current) setError((e as Error).message);
    } finally {
      locked.current = false;
      if (active.current) setBusy(false);
    }
  }
  function changeConditions() {
    setDraft((previous) => ({
      ...previous,
      step: 0,
      plan: null,
      shownIds: [],
    }));
    setEmpty(false);
    setError("");
    setNotice("");
  }
  if (loading) return <State title="Открываю ваш вечер…" loading />;
  if (id && !plan)
    return (
      <State
        title="Вечер недоступен"
        text={error}
        action={() => setRetry((value) => value + 1)}
      />
    );
  const selection = [
    draft.options.vibe,
    draft.options.duration_hours,
    draft.options.budget_max,
  ][draft.step];
  return (
    <section className="evening-page">
      <button
        className="text-button evening-back"
        disabled={busy}
        onClick={() =>
          !id && !plan && draft.step > 0
            ? setDraft((previous) => ({ ...previous, step: previous.step - 1 }))
            : navigate(-1)
        }
      >
        <ArrowLeft size={17} />
        Назад
      </button>
      <div className="eyebrow">МУР СОБЕРЁТ ВСЁ ЗА ВАС</div>
      <h1>
        Собери мой вечер<span className="brand-dot">.</span>
      </h1>
      {plan ? (
        <>
          <EveningRoute plan={plan} />
          <ErrorMessage message={error} />
          <p className="notice" role="status">
            {notice}
          </p>
          <div className="evening-actions">
            <button
              className="evening-primary"
              disabled={busy || plan.saved}
              onClick={save}
            >
              {plan.saved ? <Check size={18} /> : <Heart size={18} />}
              {plan.saved
                ? "Вечер сохранён"
                : busy
                  ? "Подождите…"
                  : "Мне нравится"}
            </button>
            {!id && (
              <button
                className="catalog-secondary"
                disabled={busy}
                onClick={generate}
              >
                <RefreshCw size={17} />
                {busy ? "Собираю…" : "Собрать другой"}
              </button>
            )}
            {id ? (
              <button
                className="text-button"
                onClick={() => {
                  rememberEveningDraft(ownerKey, {
                    options: {},
                    step: 0,
                    plan: null,
                    shownIds: [],
                  });
                  navigate("/evening");
                }}
              >
                Собрать новый вечер <ArrowRight size={16} />
              </button>
            ) : (
              <button
                className="text-button"
                disabled={busy}
                onClick={changeConditions}
              >
                Изменить условия
              </button>
            )}
          </div>
        </>
      ) : (
        <>
          <p className="subtitle">
            {user.city} · ближайший подходящий вечер в течение 7 дней
          </p>
          <div className="steps" aria-label={`Шаг ${draft.step + 1} из 3`}>
            {[0, 1, 2].map((step) => (
              <i key={step} className={step <= draft.step ? "filled" : ""} />
            ))}
          </div>
          <h2 className="evening-step-title">
            {
              [
                "Какой вайб выбираем?",
                "Сколько у вас времени?",
                "Какой бюджет на вечер?",
              ][draft.step]
            }
          </h2>
          <div className="evening-choices">
            {draft.step === 0 &&
              VIBES.map((vibe) => (
                <button
                  key={vibe.value}
                  className={`evening-choice ${draft.options.vibe === vibe.value ? "selected" : ""}`}
                  aria-pressed={draft.options.vibe === vibe.value}
                  disabled={busy}
                  onClick={() => select("vibe", vibe.value)}
                >
                  <strong>{vibe.label}</strong>
                  <small>{vibe.hint}</small>
                </button>
              ))}
            {draft.step === 1 &&
              DURATIONS.map((duration) => (
                <button
                  key={duration.value}
                  className={`evening-choice ${draft.options.duration_hours === duration.value ? "selected" : ""}`}
                  aria-pressed={draft.options.duration_hours === duration.value}
                  disabled={busy}
                  onClick={() => select("duration_hours", duration.value)}
                >
                  {duration.label}
                </button>
              ))}
            {draft.step === 2 &&
              BUDGETS.map((budget) => (
                <button
                  key={String(budget.value)}
                  className={`evening-choice ${draft.options.budget_max === budget.value ? "selected" : ""}`}
                  aria-pressed={draft.options.budget_max === budget.value}
                  disabled={busy}
                  onClick={() => select("budget_max", budget.value)}
                >
                  {budget.label}
                </button>
              ))}
          </div>
          {draft.step === 1 && (
            <p className="footnote">
              Вечер с 18:00 до 00:00. Переходы и ожидание входят в выбранное
              время; «Весь вечер» — до 6 часов.
            </p>
          )}
          {draft.step === 2 && (
            <p className="footnote">
              Бюджет на все мероприятия для одного человека. Стоимость
              приблизительная.
            </p>
          )}
          <ErrorMessage message={error} />
          {empty && (
            <State
              title="Не получилось собрать вечер"
              text="Не нашлось двух событий, совместимых по времени, расстоянию и бюджету. Попробуйте другой вайб, время или бюджет."
              label="Изменить условия"
              action={changeConditions}
            />
          )}
          <button
            className="evening-primary"
            disabled={busy || selection === undefined}
            onClick={() =>
              draft.step < 2
                ? setDraft((previous) => ({
                    ...previous,
                    step: previous.step + 1,
                  }))
                : generate()
            }
          >
            {busy
              ? "Собираю ваш вечер…"
              : draft.step < 2
                ? "Продолжить"
                : "Собрать мой вечер"}
            {draft.step < 2 ? <ArrowRight size={18} /> : <Sparkles size={18} />}
          </button>
        </>
      )}
    </section>
  );
}
