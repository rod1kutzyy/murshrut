import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "@maxhub/max-ui";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import type { Config, Preferences, User } from "../types";
import { Mascot } from "../components/Mascot";
type Category = { id: string; name: string };
import { api } from "../api";
import { State, ErrorMessage } from "../components/State";
export default function PreferencesPage({
  config,
  onSaved,
  onboarding = false,
}: {
  config: Config;
  onSaved: (user: User) => void;
  onboarding?: boolean;
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const [step, setStep] = useState(onboarding ? 0 : 2);
  const [categories, setCategories] = useState<Category[]>([]);
  const [pref, setPref] = useState<Preferences>({
    city: "Москва",
    categories: ["koncerty", "vystavki"],
    budget_max: 1500,
    companion: "friends",
    preferred_days: "any",
    preferred_time: "any",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    Promise.all([
      api<Category[]>("/categories"),
      api<Preferences | null>("/users/me/preferences"),
    ])
      .then(([cats, preferences]) => {
        if (active) {
          setCategories(cats);
          if (preferences) setPref(preferences);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (active) {
          setError(e.message);
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [retry]);
  const update = <K extends keyof Preferences>(key: K, value: Preferences[K]) =>
    setPref((p) => ({ ...p, [key]: value }));
  async function save() {
    setSaving(true);
    setError("");
    try {
      const user = await api<User>("/users/me/preferences", {
        method: "PUT",
        body: JSON.stringify(pref),
      });
      onSaved(user);
      navigate(
        onboarding
          ? location.pathname.startsWith("/events/")
            ? location.pathname
            : "/discover"
          : "/",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }
  if (loading) return <State title="Знакомимся с вашими интересами…" loading />;
  if (!categories.length)
    return (
      <State
        title="Не удалось загрузить интересы"
        text={error}
        action={() => setRetry((v) => v + 1)}
      />
    );
  const show = (s: number) => !onboarding || step === s;
  return (
    <section className={`preferences ${onboarding ? "onboarding" : ""}`}>
      {onboarding ? (
        <>
          <div className="onboard-top">
            <span className="mini-brand">муршрут.</span>
            <span>Знакомство · {step + 1} / 3</span>
          </div>
          <div className="steps">
            {[0, 1, 2].map((s) => (
              <i key={s} className={s <= step ? "filled" : ""} />
            ))}
          </div>
          <div className="welcome-cat">
            <Mascot size={110} />
          </div>
          <div className="eyebrow">ВАШ ЛИЧНЫЙ ПРОВОДНИК</div>
          <h1>
            {
              [
                "Хорошие планы\nначинаются здесь",
                "Что вас\nвдохновляет?",
                "Пара деталей —\nи мы готовы",
              ][step]
            }
          </h1>
          <p className="subtitle">
            {
              [
                "Я Мур. Помогу найти события, ради которых хочется выйти из дома.",
                "Выберите то, что любите. Остальное я подберу сам.",
                "Подберём события под ваш ритм и настроение.",
              ][step]
            }
          </p>
        </>
      ) : (
        <>
          <div className="eyebrow">ПОДБОРКА ПОД ВАС</div>
          <h1>Мой вкус</h1>
          <p className="subtitle">Планы меняются. Настройки тоже могут.</p>
        </>
      )}
      {show(0) && (
        <div className="form-section">
          <label htmlFor="city">В каком городе ищем?</label>
          {config.demo_cities.length ? (
            <select
              id="city"
              value={pref.city}
              onChange={(e) => update("city", e.target.value)}
            >
              {config.demo_cities.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          ) : (
            <input
              id="city"
              value={pref.city}
              placeholder="Например, Москва"
              onChange={(e) => update("city", e.target.value)}
            />
          )}
          <label htmlFor="companion">С кем хотите пойти?</label>
          <select
            id="companion"
            value={pref.companion}
            onChange={(e) => update("companion", e.target.value)}
          >
            <option value="solo">Самостоятельно</option>
            <option value="friends">С друзьями</option>
            <option value="partner">С партнёром</option>
            <option value="family">С семьёй</option>
            <option value="children">С детьми</option>
          </select>
        </div>
      )}
      {show(1) && (
        <div className="form-section">
          <label>
            Ваши интересы <span className="muted">Можно несколько</span>
          </label>
          <div className="chips">
            {categories.map((c) => (
              <button
                type="button"
                key={c.id}
                aria-pressed={pref.categories.includes(c.id)}
                className={`chip ${pref.categories.includes(c.id) ? "selected" : ""}`}
                onClick={() =>
                  update(
                    "categories",
                    pref.categories.includes(c.id)
                      ? pref.categories.filter((x) => x !== c.id)
                      : [...pref.categories, c.id],
                  )
                }
              >
                {pref.categories.includes(c.id) && <Check size={15} />} {c.name}
              </button>
            ))}
          </div>
        </div>
      )}
      {show(2) && (
        <div className="form-section">
          <label htmlFor="budget">Комфортный бюджет</label>
          <select
            id="budget"
            value={pref.budget_max == null ? "any" : pref.budget_max}
            onChange={(e) =>
              update(
                "budget_max",
                e.target.value === "any" ? null : Number(e.target.value),
              )
            }
          >
            <option value="0">Только бесплатно</option>
            <option value="500">До 500 ₽</option>
            <option value="1500">До 1 500 ₽</option>
            <option value="3000">До 3 000 ₽</option>
            <option value="any">Цена не важна</option>
          </select>
          <label htmlFor="days">Когда удобнее?</label>
          <div className="two-columns">
            <select
              id="days"
              value={pref.preferred_days}
              onChange={(e) => update("preferred_days", e.target.value)}
            >
              <option value="any">В любой день</option>
              <option value="weekdays">В будни</option>
              <option value="weekends">В выходные</option>
            </select>
            <select
              aria-label="Время суток"
              value={pref.preferred_time}
              onChange={(e) => update("preferred_time", e.target.value)}
            >
              <option value="any">Любое время</option>
              <option value="morning">Утро</option>
              <option value="day">День</option>
              <option value="evening">Вечер</option>
            </select>
          </div>
        </div>
      )}
      <ErrorMessage message={error} />
      <div className="form-footer">
        {onboarding && step > 0 && (
          <button
            className="back-button"
            onClick={() => setStep((s) => s - 1)}
            aria-label="Предыдущий шаг"
          >
            <ArrowLeft size={20} />
          </button>
        )}
        <Button
          stretched
          size="large"
          className="primary-button"
          disabled={
            saving || !pref.categories.length || pref.city.trim().length < 2
          }
          onClick={() =>
            onboarding && step < 2 ? setStep((s) => s + 1) : save()
          }
        >
          {saving
            ? "Сохраняем…"
            : onboarding && step < 2
              ? "Продолжить"
              : onboarding
                ? "Найти мои события"
                : "Сохранить предпочтения"}{" "}
          <ArrowRight size={18} />
        </Button>
      </div>
      {onboarding && (
        <p className="footnote">Всего минута — и город станет интереснее</p>
      )}
    </section>
  );
}
