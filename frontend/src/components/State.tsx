import { Button, Spinner } from "@maxhub/max-ui";
import { Mascot } from "./Mascot";
export function State({
  title,
  text,
  loading = false,
  action,
  label = "Попробовать снова",
}: {
  title: string;
  text?: string;
  loading?: boolean;
  action?: () => void;
  label?: string;
}) {
  return (
    <div className="state">
      <Mascot size={110} />
      <h2>{title}</h2>
      {text && <p>{text}</p>}
      {loading ? (
        <Spinner />
      ) : (
        action && <Button onClick={action}>{label}</Button>
      )}
    </div>
  );
}
export function ErrorMessage({ message }: { message: string }) {
  return message ? (
    <div role="alert" className="error">
      {message}
    </div>
  ) : null;
}
