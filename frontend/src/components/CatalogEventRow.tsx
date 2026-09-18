import { Heart, MapPin } from "lucide-react";
import type { CatalogEvent } from "../types";
import { date, time, price } from "../utils";
import { EventImage } from "./EventImage";
import { ErrorMessage } from "./State";

export default function CatalogEventRow({
  event,
  busy,
  error,
  onOpen,
  onSave,
}: {
  event: CatalogEvent;
  busy: boolean;
  error: string;
  onOpen: () => void;
  onSave: () => void;
}) {
  return (
    <article className="catalog-event">
      <button
        className="catalog-event-main"
        onClick={onOpen}
        aria-label={`Подробнее: ${event.title}`}
      >
        <div className="list-image">
          <EventImage event={event} />
        </div>
        <div className="catalog-event-copy">
          <span className="category-small">{event.category_name}</span>
          <h3>{event.title}</h3>
          <p>
            {date(event)} · {time(event)}
          </p>
          <p className="location-text">
            <MapPin size={12} />
            {event.location_name || event.city}
          </p>
          <span className={`list-price ${event.is_free ? "free" : ""}`}>
            {price(event)}
          </span>
        </div>
      </button>
      <button
        className={`catalog-heart ${event.is_saved ? "saved" : ""}`}
        disabled={busy}
        aria-busy={busy}
        aria-pressed={event.is_saved}
        aria-label={`${event.is_saved ? "Убрать из избранного" : "Сохранить"}: ${event.title}`}
        onClick={onSave}
      >
        <Heart size={20} fill={event.is_saved ? "currentColor" : "none"} />
      </button>
      <ErrorMessage message={error} />
    </article>
  );
}
