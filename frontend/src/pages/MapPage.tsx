import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MapPin, ChevronRight } from "lucide-react";
import type { Event } from "../types";
import { price } from "../utils";
import { EventMap } from "../components/EventMap";
import { api } from "../api";
import { State, ErrorMessage } from "../components/State";
export default function MapPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState("favorites");
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api<Event[]>(tab === "favorites" ? "/events/favorites" : "/recommendations")
      .then((e) => {
        if (active) setEvents(e);
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
  }, [tab, retry]);
  const select = useCallback(
    (event: Event) => navigate(`/events/${event.id}`),
    [navigate],
  );
  return (
    <section>
      <div className="eyebrow">ГОРОД ПОЛОН ВОЗМОЖНОСТЕЙ</div>
      <h1>Ближе, чем кажется</h1>
      <div className="segmented">
        <button
          className={tab === "favorites" ? "active" : ""}
          onClick={() => setTab("favorites")}
        >
          Мои события
        </button>
        <button
          className={tab === "recommendations" ? "active" : ""}
          onClick={() => setTab("recommendations")}
        >
          Для меня
        </button>
      </div>
      {loading ? (
        <State title="Расставляю точки на карте…" loading />
      ) : error ? (
        <State
          title="Не удалось загрузить карту"
          text={error}
          action={() => setRetry((r) => r + 1)}
        />
      ) : !events.length ? (
        <State
          title="Ещё нет точек на карте"
          text="Найдём событие, которое вам понравится?"
          action={() => navigate("/discover")}
          label="Начать поиск"
        />
      ) : (
        <>
          <EventMap events={events} onSelect={select} />
          <p className="footnote">
            {
              events.filter((e) => e.latitude != null && e.longitude != null)
                .length
            }{" "}
            из {events.length} событий с координатами · нажмите на метку
          </p>
          <div className="map-list">
            {events.map((e) => (
              <button key={e.id} onClick={() => select(e)}>
                <MapPin size={19} />
                <span>
                  <strong>{e.title}</strong>
                  <small>
                    {e.location_name} · {price(e)}
                  </small>
                </span>
                <ChevronRight size={16} />
              </button>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
