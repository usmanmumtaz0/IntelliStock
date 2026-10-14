import { createElement, type ComponentType } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { ProductManagement } from "./product-management";
import { UserManagement } from "./user-management";

const auth = vi.hoisted(() => ({ permissions: [] as string[] }));
vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    user: { userId: "self" },
    can: (permission: string) => auth.permissions.includes(permission),
  }),
}));

function render(component: ComponentType) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  client.setQueryData(
    ["accounts"],
    [
      {
        id: "pending",
        username: "Pending",
        email: "pending@example.com",
        role: "staff",
        is_active: false,
        signup_pending: true,
      },
    ],
  );
  client.setQueryData(
    ["products"],
    [{ id: "one", sku: "P1", name: "Milk", low_stock_threshold: 2, reorder_point: 5 }],
  );
  const html = renderToStaticMarkup(
    createElement(QueryClientProvider, { client }, createElement(component)),
  );
  client.clear();
  return html;
}

describe("permission-aware controls", () => {
  it("lets Staff read products without mutation or user management controls", () => {
    auth.permissions = ["products.read"];
    const html = render(ProductManagement);
    expect(html).toContain("Milk");
    expect(html).not.toContain("Add product");
    expect(html).not.toContain(">Edit<");
    expect(render(UserManagement)).toBe("");
  });
  it("shows product actions only with their explicit permissions", () => {
    auth.permissions = ["products.read", "products.create", "products.update"];
    const html = render(ProductManagement);
    expect(html).toContain("Add product");
    expect(html).toContain(">Edit<");
    expect(render(UserManagement)).toBe("");
  });
  it("separates account read from account creation permission", () => {
    auth.permissions = ["users.read"];
    expect(render(UserManagement)).not.toContain("Add user");
    auth.permissions.push("users.create");
    expect(render(UserManagement)).toContain("Add user");
  });
  it("uses the API creation permission for signup approval", () => {
    auth.permissions = ["users.read", "users.update"];
    expect(render(UserManagement)).not.toContain("Approve signup");
    auth.permissions = ["users.read", "users.create"];
    expect(render(UserManagement)).toContain("Approve signup");
  });
});
