export function Mascot({ size = 88 }: { size?: number }) {
  return (
    <svg
      className="mascot"
      width={size}
      height={size}
      viewBox="0 0 120 120"
      fill="none"
      role="img"
      aria-label="Кот Мур — ваш проводник"
    >
      <path
        d="M25 57L21 20Q21 13 29 19L48 33Q60 28 73 33L94 18Q101 13 99 23L95 61"
        fill="#e6edbc"
        stroke="#292e27"
        strokeWidth="3"
        strokeLinejoin="round"
      />
      <path
        d="M22 63Q20 35 60 34Q100 34 99 65Q102 96 62 98Q20 98 22 63Z"
        fill="#e6edbc"
        stroke="#292e27"
        strokeWidth="3"
      />
      <path d="M31 34L32 23L42 35M81 34L91 23L89 39" fill="#f8a27d" />
      <ellipse
        className="mascot-eye"
        cx="43"
        cy="63"
        rx="3"
        ry="5"
        fill="#292e27"
      />
      <ellipse
        className="mascot-eye"
        cx="77"
        cy="63"
        rx="3"
        ry="5"
        fill="#292e27"
      />
      <path d="M55 71L60 75L65 71Z" fill="#292e27" />
      <path
        d="M60 75V79Q54 87 49 79M60 79Q66 87 71 79M14 66L33 69M14 77L32 75M89 69L108 66M90 75L108 77"
        stroke="#292e27"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      <ellipse cx="34" cy="76" rx="7" ry="4" fill="#f8a27d" opacity=".7" />
      <ellipse cx="87" cy="76" rx="7" ry="4" fill="#f8a27d" opacity=".7" />
      <path
        d="M45 98L41 110M75 98L79 110"
        stroke="#292e27"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}
