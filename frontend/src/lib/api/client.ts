import { getAccessToken, signalUnauthorized } from "./session";

export const API_BASE_URL = (
  import.meta.env["VITE_API_URL"] ?? "http://127.0.0.1:8000/api/v1"
).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly detail?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiResponse(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (response.status === 401 && token === getAccessToken()) signalUnauthorized();
  if (!response.ok) {
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      detail = await response.text();
    }
    const message =
      typeof detail === "object" && detail !== null && "detail" in detail
        ? String((detail as { detail: unknown }).detail)
        : `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status, detail);
  }
  return response;
}

export async function apiTextRequest(path: string): Promise<string> {
  return (await apiResponse(path)).text();
}

export async function apiBlobRequest(path: string): Promise<Blob> {
  return (await apiResponse(path)).blob();
}

export function uploadRequest<T>(
  path: string,
  body: FormData,
  onProgress?: (percent: number) => void,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `${API_BASE_URL}${path}`);
    const token = getAccessToken();
    if (token) request.setRequestHeader("Authorization", `Bearer ${token}`);
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100));
    };
    request.onerror = () =>
      reject(new ApiError("Upload failed because the API could not be reached", 0));
    request.onload = () => {
      let payload: unknown;
      try {
        payload = request.responseText ? JSON.parse(request.responseText) : undefined;
      } catch {
        payload = request.responseText;
      }
      if (request.status === 401 && token === getAccessToken()) signalUnauthorized();
      if (request.status < 200 || request.status >= 300) {
        const message =
          typeof payload === "object" && payload !== null && "detail" in payload
            ? String((payload as { detail: unknown }).detail)
            : `Request failed with status ${request.status}`;
        reject(new ApiError(message, request.status, payload));
        return;
      }
      resolve(payload as T);
    };
    request.send(body);
  });
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await apiResponse(path, init);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function queryString(
  values: Record<string, string | number | boolean | null | undefined>,
): string {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  });
  const value = params.toString();
  return value ? `?${value}` : "";
}
