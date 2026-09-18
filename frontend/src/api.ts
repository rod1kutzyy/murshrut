let token = "";
export const setToken = (value: string) => {
  token = value;
};
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : response.status === 401
          ? "Откройте приложение заново, чтобы восстановить сессию."
          : "Не удалось выполнить запрос. Попробуйте снова.",
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
