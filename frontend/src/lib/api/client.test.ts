import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiRequest, apiTextRequest, ApiError } from "./client";
import { getAccessToken, setAccessToken } from "./session";

function sessionStorageStub() {
  const values = new Map<string, string>();
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
  };
}

describe("authenticated API client", () => {
  const dispatchEvent = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("window", { sessionStorage: sessionStorageStub(), dispatchEvent });
    dispatchEvent.mockClear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("attaches the session bearer token and JSON content type", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ saved: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    setAccessToken("signed-token");

    await apiRequest<{ saved: boolean }>("/resource", {
      method: "POST",
      body: JSON.stringify({ value: 1 }),
    });

    const [, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(request.headers);
    expect(headers.get("Authorization")).toBe("Bearer signed-token");
    expect(headers.get("Content-Type")).toBe("application/json");
  });

  it("downloads CSV through the authenticated client without JSON parsing", async () => {
    const csv = "sku,quantity\r\nSKU-1,4\r\n";
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(csv, { status: 200, headers: { "Content-Type": "text/csv" } }),
      );
    vi.stubGlobal("fetch", fetchMock);
    setAccessToken("report-token");
    expect(await apiTextRequest("/reports/export?kind=inventory")).toBe(csv);
    const [, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(new Headers(request.headers).get("Authorization")).toBe("Bearer report-token");
  });

  it("does not download a failed export as a successful CSV file", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ detail: "Narrow the report" }), { status: 413 }),
        ),
    );
    await expect(apiTextRequest("/reports/export")).rejects.toMatchObject({
      status: 413,
      message: "Narrow the report",
    });
  });

  it("clears an expired session and exposes the backend error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Could not validate credentials" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    setAccessToken("expired-token");

    await expect(apiRequest("/protected")).rejects.toEqual(
      expect.objectContaining<ApiError>({
        name: "ApiError",
        status: 401,
        message: "Could not validate credentials",
      }),
    );
    expect(getAccessToken()).toBeNull();
    expect(dispatchEvent).toHaveBeenCalledOnce();
  });
});
