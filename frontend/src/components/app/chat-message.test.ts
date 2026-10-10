import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ChatMessage } from "./chat-message";
import type { ChatTurn } from "@/lib/api/chat";

const turn: ChatTurn = {
  id: "turn-1",
  request_id: "request-1",
  sequence: 1,
  question: "Show inventory",
  answer: "<script>alert(1)</script>",
  sources: [
    { id: "safe", kind: "inventory", label: "Inventory", href: "/inventory" },
    { id: "unsafe", kind: "inventory", label: "Unsafe", href: "javascript:alert(1)" },
  ],
  mode: "fallback",
  notice: "Provider unavailable",
  created_at: "2026-10-11T12:00:00Z",
};

describe("chat message presentation", () => {
  it("escapes answer content and preserves safe source links only", () => {
    const html = renderToStaticMarkup(createElement(ChatMessage, { turn }));
    expect(html).toContain("&lt;script&gt;");
    expect(html).not.toContain("<script>");
    expect(html).toContain('href="/inventory"');
    expect(html).not.toContain("javascript:");
  });
  it("keeps fallback and generation details visible without claiming AI success", () => {
    const html = renderToStaticMarkup(createElement(ChatMessage, { turn }));
    expect(html).toContain("Local fallback");
    expect(html).toContain("Provider unavailable");
    expect(html).toContain('aria-label="Copy answer"');
    expect(html).not.toContain("OpenRouter");
  });
});
