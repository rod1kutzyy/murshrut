import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@maxhub/max-ui";
import {
  Settings,
  Sparkles,
  MapPin,
  ChevronRight,
  Compass,
  ArrowRight,
} from "lucide-react";
import type { Event } from "../types";
import { date, time, price } from "../utils";
import { Mascot } from "../components/Mascot";
import { EventImage } from "../components/EventImage";
import { api } from "../api";
import { State, ErrorMessage } from "../components/State";
export default function MyEvents() {
  const navigate = useNavigate();
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api<Event[]>("/events/favorites")
      .then((data) => {
        if (active) setEvents(data);
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
  }, [retry]);
  return (
    <section>
      <div className="page-heading">
        <div>
          <div className="eyebrow">ПЛАНЫ, КОТОРЫЕ РАДУЮТ</div>
          <h1>
            Мои события <sup>{events.length || ""}</sup>
          </h1>
        </div>
        <button
          className="icon-button"
          aria-label="Настройки"
          onClick={() => navigate("/profile")}
        >
          <Settings size={22} />
        </button>
      </div>
      <div className="cat-note">
        <Mascot size={55} />
        <p>
          {events.length ? (
            <>
              Хороший выбор!
              <br />
              <strong>Осталось выбрать компанию.</strong>
            </>
          ) : (
            <>
              Ваш следующий хороший вечер
              <br />
              <strong>уже где-то рядом.</strong>
            </>
          )}
        </p>
        <Sparkles size={20} />
      </div>
      {loading ? (
        <State title="Собираю ваши планы…" loading />
      ) : error ? (
        <State
          title="Не удалось загрузить события"
          text={error}
          action={() => setRetry((v) => v + 1)}
        />
      ) : events.length ? (
        <div className="event-list">
          {events.map((e) => (
            <button
              className="event-list-item"
              key={e.id}
              onClick={() => navigate(`/events/${e.id}`)}
            >
              <div className="list-image">
                <EventImage event={e} />
              </div>
              <div>
                <span className="category-small">{e.category_name}</span>
                <h3>{e.title}</h3>
                <p>
                  {date(e)} · {time(e)}
                </p>
                <p className="location-text">
                  <MapPin size={12} />
                  {e.location_name}
                </p>
                <span className="list-price">{price(e)}</span>
              </div>
              <ChevronRight size={17} />
            </button>
          ))}
        </div>
      ) : (
        <State
          title="Пока без планов"
          text="Свайпните событие вправо — Мур сохранит его здесь."
        />
      )}
      <Button
        stretched
        size="large"
        className="primary-button search-button"
        onClick={() => navigate("/discover")}
      >
        <Compass size={20} /> Начать поиск <ArrowRight size={18} />
      </Button>
    </section>
  );
}
