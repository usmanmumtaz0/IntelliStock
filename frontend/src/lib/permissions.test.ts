import { describe, expect, it } from "vitest";
import { authorizationKey, can, canVisit } from "./permissions";
import type { AuthUser } from "./api/types";

const user: AuthUser = {
  userId: "one",
  username: "Tester",
  email: "test@example.com",
  role: "admin",
  permissions: [],
};
describe("server permission driven access", () => {
  it("never infers privileges from the role label", () => {
    expect(can(user, "users.read")).toBe(false);
    expect(canVisit(user, "/inventory")).toBe(false);
  });
  it("denies anonymous and unknown routes", () => {
    expect(canVisit(null, "/settings")).toBe(false);
    expect(canVisit(user, "/unknown")).toBe(false);
    expect(canVisit(user, "/settings")).toBe(true);
  });
  it("checks exact server permission and trailing slashes", () => {
    const staff = {
      ...user,
      role: "staff" as const,
      permissions: ["inventory.read", "requests.read_own"],
    };
    expect(canVisit(staff, "/inventory/")).toBe(true);
    expect(canVisit(staff, "/requests")).toBe(true);
    expect(can(staff, "inventory.adjust_stock")).toBe(false);
    expect(canVisit(staff, "/reports")).toBe(false);
  });
  it("isolates account and permission changes but ignores permission order", () => {
    expect(authorizationKey(user)).not.toBe(authorizationKey({ ...user, userId: "two" }));
    expect(authorizationKey(user)).not.toBe(
      authorizationKey({ ...user, permissions: ["users.read"] }),
    );
    expect(authorizationKey({ ...user, permissions: ["a", "b"] })).toBe(
      authorizationKey({ ...user, permissions: ["b", "a"] }),
    );
  });
});
