import { afterEach, describe, expect, it, vi } from "vitest";
import { operations } from "./operations";

afterEach(() => vi.unstubAllGlobals());

function mockRequest() {
  const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("operational API contracts", () => {
  it("does not send immutable SKU when editing a product", async () => {
    const fetchMock = mockRequest();
    await operations.saveProduct(
      { sku: "SKU", name: "Product", description: null, low_stock_threshold: 3, reorder_point: 10 },
      "product-1",
    );
    const [url, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/products/product-1");
    expect(request.method).toBe("PUT");
    expect(JSON.parse(String(request.body))).not.toHaveProperty("sku");
  });
  it("sends inventory identity, audit reason and concurrency version", async () => {
    const fetchMock = mockRequest();
    const input = {
      quantity: 4,
      reason: "Physical count",
      expected_updated_at: "2026-10-10T12:00:00",
    };
    await operations.correctInventory("inventory-zone-2", input);
    const [url, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/inventory/inventory-zone-2/corrections");
    expect(JSON.parse(String(request.body))).toEqual(input);
  });
});
