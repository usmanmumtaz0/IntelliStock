import { afterEach, describe, expect, it, vi } from "vitest";
import { requests, submissionFromForm } from "./requests";

afterEach(() => vi.unstubAllGlobals());
describe("operational requests", () => {
  it("only includes a counted quantity for physical counts, without client-selected authority", () => {
    const data = new FormData();
    data.set("inventory", "item-1");
    data.set("reason", "  Shelf checked  ");
    data.set("quantity", "0");
    data.set("status", "approved");
    data.set("submitter_id", "admin");
    expect(submissionFromForm(data, "physical_count")).toEqual({
      inventory_id: "item-1",
      kind: "physical_count",
      quantity: 0,
      reason: "Shelf checked",
    });
    expect(submissionFromForm(data, "restock")).toEqual({
      inventory_id: "item-1",
      kind: "restock",
      reason: "Shelf checked",
    });
    expect(submissionFromForm(data, "discrepancy")).not.toHaveProperty("quantity");
  });
  it("paginates scoped lists and encodes review identifiers", async () => {
    const fetcher = vi
      .fn()
      .mockImplementation(() => Promise.resolve(new Response("[]", { status: 200 })));
    vi.stubGlobal("fetch", fetcher);
    await requests.list(50);
    await requests.activity(100);
    await requests.review("id/one", { decision: "rejected", reason: "Please recount" });
    expect(fetcher.mock.calls[0]?.[0]).toContain("/requests?limit=50&offset=50");
    expect(fetcher.mock.calls[1]?.[0]).toContain("/operational-audit?limit=50&offset=100");
    expect(fetcher.mock.calls[2]?.[0]).toContain("/requests/id%2Fone/review");
    expect(JSON.parse(fetcher.mock.calls[2]?.[1].body)).toEqual({
      decision: "rejected",
      reason: "Please recount",
    });
  });
  it.each([403, 409])("does not turn a rejected review (%s) into success", async (status) => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(new Response(JSON.stringify({ detail: "Review denied" }), { status })),
    );
    await expect(
      requests.review("one", { decision: "approved", reason: "Count checked" }),
    ).rejects.toMatchObject({ status });
  });
});
