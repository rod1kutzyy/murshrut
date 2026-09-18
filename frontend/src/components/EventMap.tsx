import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Event } from "../types";
export function EventMap({
  events,
  onSelect,
  compact = false,
}: {
  events: Event[];
  onSelect?: (e: Event) => void;
  compact?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const points = events.filter(
      (e) => e.latitude != null && e.longitude != null,
    );
    const map = L.map(ref.current, { scrollWheelZoom: false }).setView(
      points.length
        ? [points[0].latitude!, points[0].longitude!]
        : [55.7558, 37.6173],
      12,
    );
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(map);
    for (const event of points) {
      const marker = L.marker([event.latitude!, event.longitude!], {
        icon: L.divIcon({
          className: "event-pin",
          html: "<span>♥</span>",
          iconSize: [34, 40],
          iconAnchor: [17, 40],
        }),
      }).addTo(map);
      const popup = document.createElement("button");
      popup.type = "button";
      popup.textContent = event.title;
      popup.addEventListener("click", () => onSelect?.(event));
      marker.bindPopup(popup);
    }
    if (points.length > 1)
      map.fitBounds(
        L.latLngBounds(
          points.map((e) => [e.latitude!, e.longitude!] as L.LatLngTuple),
        ),
        { padding: [35, 35], maxZoom: 14 },
      );
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(ref.current);
    return () => {
      observer.disconnect();
      map.remove();
    };
  }, [events, onSelect]);
  return (
    <div
      className={`event-map ${compact ? "compact" : ""}`}
      ref={ref}
      aria-label="Карта мероприятий"
    />
  );
}
