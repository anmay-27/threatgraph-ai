export class ApiError extends Error { constructor(message:string,public status:number){super(message);} }
export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch("/api/v1" + path, options);
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Server did not respond" }));
    if(response.status===401 && !path.startsWith('/auth/'))window.dispatchEvent(new Event('session-expired'));
    throw new ApiError(
      typeof error.detail === "string"
        ? error.detail
        : "Please check your input and try again.", response.status,
    );
  }
  return response.json();
}
