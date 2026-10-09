import { describe, expect, it } from "vitest";
import { alertSeverityTone, confidencePercent, inventoryTrustState } from "./view-models";
import type { InventoryDto } from "./api";

const inventory = (overrides: Partial<InventoryDto> = {}): InventoryDto => ({
  id: "inventory-1",
  zone_id: "zone-1",
  product_id: "product-1",
  sku: "SKU-1",
  name: "Test product",
  current_quantity: 8,
  threshold: 3,
  status: "adequate",
  verified: true,
  pending_quantity: null,
  confidence: 0.92,
  last_observation_time: null,
  observations_count: 3,
  updated_at: "2026-01-01T00:00:00Z",
  ...overrides,
});

describe("inventoryTrustState", () => {
  it("keeps a verified committed quantity trusted", () => {
    expect(inventoryTrustState(inventory())).toBe("verified");
  });

  it("marks a differing observation as pending", () => {
    expect(inventoryTrustState(inventory({ pending_quantity: 6 }))).toBe("pending");
  });

  it("flags an unverified record without a pending delta", () => {
    expect(inventoryTrustState(inventory({ verified: false }))).toBe("flagged");
  });
});

describe("wire value presentation", () => {
  it("normalizes fractional and percentage confidence values", () => {
    expect(confidencePercent(0.934)).toBe(93.4);
    expect(confidencePercent(93.4)).toBe(93.4);
  });

  it("maps alert severities to stable display tones", () => {
    expect(alertSeverityTone("CRITICAL")).toBe("critical");
    expect(alertSeverityTone("MEDIUM")).toBe("warning");
    expect(alertSeverityTone("INFO")).toBe("info");
  });
});
