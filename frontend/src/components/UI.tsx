import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  stretched?: boolean;
  size?: "large";
  variant?: "primary" | "secondary";
};

export function Button({
  children,
  stretched = false,
  size,
  variant = "primary",
  className = "",
  type = "button",
  ...props
}: ButtonProps) {
  const classes = [
    "ui-button",
    stretched ? "ui-button-stretched" : "",
    size === "large" ? "ui-button-large" : "",
    variant === "secondary" ? "ui-button-secondary" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button type={type} className={classes} {...props}>
      <span>{children}</span>
    </button>
  );
}

export function Spinner() {
  return <span className="ui-spinner" role="status" aria-label="Загрузка" />;
}
