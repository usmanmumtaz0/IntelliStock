import { afterEach, describe, expect, it, vi } from "vitest";
import { chat, safeSourceHref } from "./chat";

afterEach(() => vi.unstubAllGlobals());

describe("assistant contracts", () => {
  it("sends the same request ID for an explicit retry", async () => {
    const fetchMock = vi
      .fn()
      .mockImplementation(() => Promise.resolve(new Response("{}", { status: 200 })));
    vi.stubGlobal("fetch", fetchMock);
    const input = { request_id: "stable-request-id", question: "Show inventory" };
    await chat.ask("conversation-1", input);
    await chat.ask("conversation-1", input);
    for (const call of fetchMock.mock.calls) {
      const [url, request] = call as [string, RequestInit];
      expect(url).toContain("/chat/conversations/conversation-1/turns");
      expect(JSON.parse(String(request.body))).toEqual(input);
    }
  });

  it("only permits internal source destinations", () => {
    expect(safeSourceHref("/inventory?record=123")).toBe("/inventory?record=123");
    expect(safeSourceHref("/alerts")).toBe("/alerts");
    expect(safeSourceHref("/reports")).toBe("/reports");
    for (const href of [
      "javascript:alert(1)",
      "https://example.com",
      "//example.com",
      "/admin",
      "/inventory\\evil",
      "/inventory\n",
    ]) {
      expect(safeSourceHref(href)).toBeNull();
    }
  });
});
