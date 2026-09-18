import { useNavigate } from "react-router-dom";
import { Clock, MapPin, Footprints, ArrowRight } from "lucide-react";
import type { EveningPlan } from "../types";
import { eveningCost, eveningDate, eveningDuration, VIBES } from "../evening";
import { time } from "../utils";
import { EventImage } from "./EventImage";

export default function EveningRoute({ plan }: { plan: EveningPlan }) {
  const navigate = useNavigate();
  return (
    <div className="evening-route">
      <div className="evening-result-heading">
        <div className="eyebrow">ВАШ ГОТОВЫЙ ВЕЧЕР</div>
        <h2>
          {VIBES.find((vibe) => vibe.value === plan.vibe)?.label || "Мой вечер"}
        </h2>
        <p>
          {eveningDate(plan)} · {plan.city}
        </p>
      </div>
      <div className="evening-summary" aria-label="Итоги вечера">
        <div>
          <strong>{eveningCost(plan)}</strong>
          <span>на одного человека</span>
        </div>
        <div>
          <strong>{eveningDuration(plan.duration_minutes)}</strong>
          <span>с переходами и ожиданием</span>
        </div>
        <div>
          <strong>{plan.event_count}</strong>
          <span>событий</span>
        </div>
      </div>
      <p className="footnote">
        Цены приблизительные, без дополнительных расходов. Время событий —
        местное.
      </p>
      {!!plan.warnings.length && (
        <div className="evening-warning" role="status">
          {plan.warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </div>
      )}
      <div className="evening-reasons">
        {plan.reasons.map((reason) => (
          <span className="chip" key={reason}>
            {reason}
          </span>
        ))}
      </div>
      <ol className="evening-timeline">
        {plan.events.map((event, index) => (
          <li key={event.id}>
            <div className="evening-stop-number" aria-hidden="true">
              {index + 1}
            </div>
            <article className="evening-event">
              <button
                className="evening-event-image"
                aria-label={`Открыть карточку: ${event.title}`}
                onClick={() => navigate(`/events/${event.id}`)}
              >
                <EventImage event={event} />
              </button>
              <div className="evening-event-body">
                <span className="category-small">{event.category_name}</span>
                <h3>{event.title}</h3>
                <p className="evening-event-time">
                  <Clock size={14} />
                  {time(event)}–{time({ ...event, start_date: event.end_date })}
                </p>
                <p className="location-text">
                  <MapPin size={14} />
                  {event.location_name || event.city}
                </p>
                <p className="footnote">{event.address}</p>
                <p className="evening-description">
                  {event.description || "Подробности в карточке мероприятия."}
                </p>
                <strong className="list-price">
                  {event.is_free
                    ? "Бесплатно"
                    : event.estimated_price === null
                      ? "Цена уточняется"
                      : `≈ ${event.estimated_price.toLocaleString("ru-RU")} ₽`}
                </strong>
                {!!event.reasons.length && (
                  <p className="footnote">{event.reasons.join(" · ")}</p>
                )}
                <button
                  className="text-button evening-details"
                  onClick={() => navigate(`/events/${event.id}`)}
                >
                  Подробнее <ArrowRight size={15} />
                </button>
              </div>
            </article>
            {event.next_transfer && (
              <div className="evening-transfer">
                <Footprints size={17} />
                <span>
                  Около {event.next_transfer.minutes} мин пешком · ≈{" "}
                  {event.next_transfer.distance_km.toLocaleString("ru-RU")} км
                  <small>Оценка с запасом, путь может отличаться</small>
                </span>
              </div>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
