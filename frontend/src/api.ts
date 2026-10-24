export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch("/api/v1" + path, options);
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Server did not respond" }));
    throw new Error(
      typeof error.detail === "string"
        ? error.detail
        : "Please check your input and try again.",
    );
  }
  return response.json();
}
