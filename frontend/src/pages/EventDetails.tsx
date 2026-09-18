import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@maxhub/max-ui";
import {
  ArrowLeft,
  Share2,
  CalendarDays,
  Clock,
  MapPin,
  Ticket,
  ArrowRight,
  Check,
  Heart,
} from "lucide-react";
import type { Event, Config } from "../types";
import { date, time, price, share } from "../utils";
import { EventImage } from "../components/EventImage";
import { EventMap } from "../components/EventMap";
import { api } from "../api";
import { State, ErrorMessage } from "../components/State";
export default function EventDetails({ config }: { config: Config }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [event, setEvent] = useState<Event | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    Promise.all([
      api<Event>(`/events/${id}`),
      api<Event[]>("/events/favorites"),
    ])
      .then(([e, favorites]) => {
        if (active) {
          setEvent(e);
          setSaved(favorites.some((f) => f.id === id));
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [id, retry]);
  const select = useCallback(
    (e: Event) => navigate(`/events/${e.id}`),
    [navigate],
  );
  if (loading) return <State title="Открываю событие…" loading />;
  if (!event)
    return (
      <State
        title="Событие недоступно"
        text={error}
        action={() => setRetry((r) => r + 1)}
      />
    );
  async function toggleSaved() {
    if (!event) return;
    setBusy(true);
    setError("");
    try {
      await api(
        `/events/${event.id}/reaction`,
        saved
          ? { method: "DELETE" }
          : { method: "POST", body: JSON.stringify({ reaction: "like" }) },
      );
      setSaved(!saved);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="detail">
      <div className="detail-toolbar">
        <button className="text-button" onClick={() => navigate(-1)}>
          <ArrowLeft size={18} /> Назад
        </button>
        <button
          className="icon-button"
          aria-label="Поделиться"
          onClick={() =>
            share(event, config.max_bot_name)
              .then(setNotice)
              .catch((e) => {
                if (e.name !== "AbortError")
                  setError("Не удалось поделиться. Попробуйте снова.");
              })
          }
        >
          <Share2 size={20} />
        </button>
      </div>
      <div className="detail-image">
        <EventImage key={event.id} event={event} />
        <span className="category-tag">{event.category_name}</span>
      </div>
      <h1>{event.title}</h1>
      <div className="detail-facts">
        <div>
          <CalendarDays size={21} />
          <span>
            <strong>{date(event)}</strong>
            <small>
              <Clock size={12} />
              {time(event)} · местное время
            </small>
          </span>
        </div>
        <div>
          <MapPin size={21} />
          <span>
            <strong>{event.location_name || event.city}</strong>
            <small>
              {event.city} · {event.address}
            </small>
          </span>
        </div>
        <div>
          <Ticket size={21} />
          <span>
            <strong>{price(event)}</strong>
            <small>
              {event.price_max != null && event.price_max !== event.price_min
                ? `До ${event.price_max} ₽`
                : "Пора строить планы"}
            </small>
          </span>
        </div>
      </div>
      <h2>О событии</h2>
      <p className="description">
        {event.description || "Подробности на сайте организатора."}
      </p>
      {event.image_credit && (
        <p className="footnote">Изображение: {event.image_credit}</p>
      )}
      <h2>Где встречаемся</h2>
      {event.latitude != null && event.longitude != null ? (
        <>
          <EventMap events={[event]} compact onSelect={select} />
          <a
            className="external-link"
            target="_blank"
            rel="noreferrer"
            href={`https://www.openstreetmap.org/?mlat=${event.latitude}&mlon=${event.longitude}#map=16/${event.latitude}/${event.longitude}`}
          >
            Открыть большую карту <ArrowRight size={15} />
          </a>
        </>
      ) : (
        <p className="subtitle">
          {event.address || "Место уточняется"}. Координаты не указаны.
        </p>
      )}
      <ErrorMessage message={error} />
      <div className="notice" role="status">
        {notice}
      </div>
      <Button
        stretched
        size="large"
        className="primary-button"
        disabled={busy}
        onClick={toggleSaved}
      >
        {saved ? <Check size={19} /> : <Heart size={19} />}{" "}
        {saved ? "Убрать из моих событий" : "Хочу пойти"}
      </Button>
      <Button
        stretched
        variant="secondary"
        className="share-button"
        onClick={() =>
          share(event, config.max_bot_name)
            .then(setNotice)
            .catch((e) => {
              if (e.name !== "AbortError") setError("Не удалось поделиться.");
            })
        }
      >
        <Share2 size={17} /> Поделиться
      </Button>
      {event.source_url && (
        <a
          className="external-link"
          href={event.source_url}
          target="_blank"
          rel="noreferrer"
        >
          На сайт мероприятия <ArrowRight size={15} />
        </a>
      )}
    </section>
  );
}
