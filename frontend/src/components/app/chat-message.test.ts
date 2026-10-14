import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ChatMessage } from "./chat-message";
import type { ChatTurn } from "@/lib/api/chat";

const turn: ChatTurn = {
  id: "turn",
  request_id: "request",
  sequence: 1,
  question: "Where is the milk?",
  answer: "Milk is on Shelf A.",
  mode: "local",
  notice: null,
  created_at: "2026-10-14T12:00:00Z",
  sources: [],
};

describe("chat evidence", () => {
  it("shows plain-language product, shelf, source and timestamps", () => {
    const html = renderToStaticMarkup(
      createElement(ChatMessage, {
        turn: {
          ...turn,
          sources: [
            {
              kind: "inventory",
              id: "1",
              label: "Milk / Shelf A",
              href: "/inventory?record=1",
              sku: "MILK-1",
              shelf: "Shelf A",
              updated_at: "2026-10-14T11:00:00Z",
              retrieved_at: "2026-10-14T12:00:00Z",
            },
          ],
        },
      }),
    );
    for (const text of [
      "Product code: MILK-1",
      "Shelf: Shelf A",
      "Source: inventory",
      "Record updated (UTC)",
      "Retrieved (UTC)",
    ]) {
      expect(html).toContain(text);
    }
    expect(html).not.toContain("SKU:");
  });
  it("still renders older saved answers without evidence timestamps", () => {
    expect(renderToStaticMarkup(createElement(ChatMessage, { turn }))).toContain(
      "Milk is on Shelf A.",
    );
  });
});
