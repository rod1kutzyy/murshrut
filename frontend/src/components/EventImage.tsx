import { useState } from "react";
import type { Event } from "../types";
export function EventImage({ event }: { event: Event }) {
  const [failed, setFailed] = useState(false);
  const fallback = ["koncerty"].includes(event.category)
    ? "jazz"
    : event.category === "spektakli"
      ? "theatre"
      : event.category === "kino"
        ? "cinema"
        : "art";
  return (
    <img
      src={
        !failed && event.image_url ? event.image_url : `/art/${fallback}.svg`
      }
      alt=""
      onError={() => setFailed(true)}
    />
  );
}
