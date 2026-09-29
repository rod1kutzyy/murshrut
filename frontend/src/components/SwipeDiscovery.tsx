import { useEffect, useRef, useState, type PointerEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  CalendarDays,
  MapPin,
  ArrowRight,
  Sparkles,
  ThumbsDown,
  Heart,
} from "lucide-react";
import type { Event } from "../types";
import { date, time, price } from "../utils";
import { EventImage } from "./EventImage";
import { api } from "../api";
import { State, ErrorMessage } from "./State";
export default function SwipeDiscovery() {
  const navigate = useNavigate();
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [retry, setRetry] = useState(0);
  const cardRef = useRef<HTMLElement>(null);
  const likeCueRef = useRef<HTMLDivElement>(null);
  const dislikeCueRef = useRef<HTMLDivElement>(null);
  const locked = useRef(false);
  const offset = useRef(0);
  const animationFrame = useRef<number | null>(null);
  const [dragging, setDragging] = useState(false);
  const start = useRef<{ x: number; y: number } | null>(null);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api<Event[]>("/recommendations")
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
  useEffect(
    () => () => {
      if (animationFrame.current !== null)
        cancelAnimationFrame(animationFrame.current);
    },
    [],
  );
  const event = events[0];

  function maxDragOffset() {
    const cardWidth = cardRef.current?.offsetWidth ?? 320;
    return Math.max(0, cardWidth - 72);
  }

  function clampOffset(value: number) {
    const limit = maxDragOffset();
    return Math.max(-limit, Math.min(limit, value));
  }

  function setCueProgress(value: number) {
    const progress = Math.min(1, Math.max(0, (Math.abs(value) - 18) / 78));
    const activeCue = value > 0 ? likeCueRef.current : dislikeCueRef.current;
    const inactiveCue = value > 0 ? dislikeCueRef.current : likeCueRef.current;
    if (activeCue) {
      activeCue.style.opacity = String(progress);
      activeCue.style.transform = `translate(-50%, -50%) scale(${0.76 + progress * 0.24})`;
    }
    if (inactiveCue) {
      inactiveCue.style.opacity = "0";
      inactiveCue.style.transform = "translate(-50%, -50%) scale(.76)";
    }
  }

  function applyOffset(value: number) {
    const nextOffset = clampOffset(value);
    offset.current = nextOffset;
    if (cardRef.current) {
      const rotation = Math.max(-10, Math.min(10, nextOffset / 28));
      cardRef.current.style.transform = `translate3d(${nextOffset}px, 0, 0) rotate(${rotation}deg)`;
    }
    setCueProgress(nextOffset);
  }

  function scheduleOffset(value: number) {
    if (animationFrame.current !== null)
      cancelAnimationFrame(animationFrame.current);
    animationFrame.current = requestAnimationFrame(() => {
      applyOffset(value);
      animationFrame.current = null;
    });
  }

  function resetCard() {
    if (animationFrame.current !== null) {
      cancelAnimationFrame(animationFrame.current);
      animationFrame.current = null;
    }
    applyOffset(0);
  }

  async function react(reaction: "like" | "dislike") {
    if (!event || locked.current) return;
    locked.current = true;
    start.current = null;
    setDragging(false);
    setBusy(true);
    setError("");
    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    const direction = reaction === "like" ? 1 : -1;
    setCueProgress(direction * 96);
    const animation = cardRef.current?.animate(
      [
        {
          transform: `translate3d(${offset.current}px, 0, 0) rotate(${Math.max(-10, Math.min(10, offset.current / 28))}deg)`,
          opacity: 1,
        },
        {
          transform: `translate3d(${direction * (window.innerWidth + 400)}px, 0, 0) rotate(${direction * 18}deg)`,
          opacity: 0,
        },
      ],
      {
        duration: reduced ? 0 : 380,
        easing: "cubic-bezier(.22,.72,.18,1)",
        fill: "forwards",
      },
    );
    const finished = animation?.finished.catch(() => {});
    try {
      await api(`/events/${event.id}/reaction`, {
        method: "POST",
        body: JSON.stringify({ reaction }),
      });
      await finished;
      setNotice(
        reaction === "like"
          ? "Сохранено в «Мои события» ♡"
          : "Учту это в следующих подборках",
      );
      setEvents((current) => current.filter((item) => item.id !== event.id));
      resetCard();
      if (events.length === 1) setRetry((r) => r + 1);
    } catch (e) {
      setError((e as Error).message);
      resetCard();
    } finally {
      animation?.cancel();
      locked.current = false;
      setBusy(false);
    }
  }
  function pointerDown(e: PointerEvent) {
    if (
      locked.current ||
      !e.isPrimary ||
      e.button !== 0 ||
      (e.target as HTMLElement).closest("button, a")
    )
      return;
    setDragging(true);
    start.current = { x: e.clientX, y: e.clientY };
    e.currentTarget.setPointerCapture(e.pointerId);
  }
  function pointerMove(e: PointerEvent) {
    if (start.current) scheduleOffset(e.clientX - start.current.x);
  }
  function pointerUp(e: PointerEvent) {
    if (!start.current) return;
    const dx = e.clientX - start.current.x,
      dy = e.clientY - start.current.y;
    if (animationFrame.current !== null) {
      cancelAnimationFrame(animationFrame.current);
      animationFrame.current = null;
    }
    applyOffset(dx);
    start.current = null;
    setDragging(false);
    if (e.currentTarget.hasPointerCapture(e.pointerId))
      e.currentTarget.releasePointerCapture(e.pointerId);
    if (Math.abs(dx) > 90 && Math.abs(dx) > Math.abs(dy) * 1.3)
      void react(dx > 0 ? "like" : "dislike");
    else resetCard();
  }
  return (
    <section className="discover">
      {loading ? (
        <State title="Ищу что-нибудь интересное…" loading />
      ) : !event ? (
        error ? (
          <State
            title="Не удалось загрузить мероприятия"
            text={error}
            action={() => setRetry((r) => r + 1)}
          />
        ) : (
          <State
            title="На сегодня это всё"
            text="Попробуйте изменить интересы или вернитесь чуть позже."
            label="Изменить интересы"
            action={() => navigate("/profile")}
          />
        )
      ) : (
        <>
          <div className="card-stack">
            <div className="stack-under" />
            <article
              key={event.id}
              ref={cardRef}
              aria-busy={busy}
              className={`swipe-card ${busy ? "busy" : ""} ${dragging ? "dragging" : ""}`}
              onPointerDown={pointerDown}
              onPointerMove={pointerMove}
              onPointerUp={pointerUp}
              onDragStart={(e) => e.preventDefault()}
              onLostPointerCapture={() => {
                start.current = null;
                setDragging(false);
              }}
              onPointerCancel={() => {
                start.current = null;
                setDragging(false);
                resetCard();
              }}
            >
              <div className="hero-image">
                <EventImage key={event.id} event={event} />
                <span className="category-tag">{event.category_name}</span>
                <div
                  ref={likeCueRef}
                  className="swipe-cue like"
                  aria-hidden="true"
                >
                  <Heart size={38} strokeWidth={1.8} />
                </div>
                <div
                  ref={dislikeCueRef}
                  className="swipe-cue dislike"
                  aria-hidden="true"
                >
                  <ThumbsDown size={36} strokeWidth={1.8} />
                </div>
              </div>
              <div className="card-content">
                <div className="card-date">
                  <CalendarDays size={15} />
                  {date(event)} <span>·</span> {time(event)}
                </div>
                <h2>{event.title}</h2>
                <div className="card-location">
                  <MapPin size={15} />
                  {event.location_name}
                </div>
                <div className="card-bottom">
                  <span className={`price-pill ${event.is_free ? "free" : ""}`}>
                    {price(event)}
                  </span>
                  <button
                    onClick={() => navigate(`/events/${event.id}`)}
                    className="details-link"
                  >
                    Подробнее <ArrowRight size={16} />
                  </button>
                </div>
                <div className="match-reason">
                  <Sparkles size={13} />
                  {event.reasons.find((r) => r === "По вашим интересам") ||
                    event.reasons[0] ||
                    "Новые впечатления"}
                </div>
              </div>
            </article>
          </div>
          <ErrorMessage message={error} />
          <div className="reactions">
            <div>
              <button
                className="reaction dislike"
                disabled={busy}
                aria-label="Не интересно"
                onClick={() => react("dislike")}
              >
                <ThumbsDown size={26} />
              </button>
              <span>Не моё</span>
            </div>
            <div>
              <button
                className="reaction like"
                disabled={busy}
                aria-label="Нравится"
                onClick={() => react("like")}
              >
                <Heart size={30} />
              </button>
              <span>Хочу пойти</span>
            </div>
          </div>
          <p className="swipe-help">
            Свайпните влево или вправо — как чувствуете
          </p>
        </>
      )}
      <div className="notice" role="status">
        {notice}
      </div>
    </section>
  );
}
