import { describe, expect, it } from "vitest";
import { canReviewOperationalRequest, type OperationalRequest } from "./requests";
import type { AuthUser } from "./types";

const baseUser: AuthUser = {
  userId: "reviewer",
  username: "Reviewer",
  email: "reviewer@example.com",
  role: "manager",
  permissions: ["requests.review"],
};

const request: OperationalRequest = {
  id: "request-one",
  inventory_id: "inventory-one",
  submitter_id: "staff-one",
  kind: "discrepancy",
  reason: "Verified mismatch",
  quantity: null,
  status: "pending",
  review_tier: "manager",
  reviewer_id: null,
  review_reason: null,
  reviewed_at: null,
  created_at: "2026-10-21T00:00:00Z",
  updated_at: "2026-10-21T00:00:00Z",
};

describe("request review routing", () => {
  it("allows Managers to review Staff requests but not Admin escalations", () => {
    expect(canReviewOperationalRequest(request, baseUser, true)).toBe(true);
    expect(canReviewOperationalRequest({ ...request, review_tier: "admin" }, baseUser, true)).toBe(
      false,
    );
  });

  it("allows Admin review at either tier while preventing self-review", () => {
    const admin = { ...baseUser, role: "admin" as const };
    expect(canReviewOperationalRequest({ ...request, review_tier: "admin" }, admin, true)).toBe(
      true,
    );
    expect(
      canReviewOperationalRequest({ ...request, submitter_id: admin.userId }, admin, true),
    ).toBe(false);
    expect(canReviewOperationalRequest(request, admin, false)).toBe(false);
  });
});
