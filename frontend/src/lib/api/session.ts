const TOKEN_KEY = "intellistock.access_token";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(TOKEN_KEY);
}

export function setAccessToken(token: string): void {
  if (typeof window !== "undefined") window.sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearAccessToken(): void {
  if (typeof window !== "undefined") window.sessionStorage.removeItem(TOKEN_KEY);
}

export function signalUnauthorized(): void {
  clearAccessToken();
  if (typeof window !== "undefined") window.dispatchEvent(new Event("intellistock:unauthorized"));
}
