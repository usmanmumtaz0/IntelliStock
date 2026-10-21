import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({
  permissions: [] as string[],
  theme: "dark" as "dark" | "light",
  setTheme: vi.fn(),
}));

vi.mock("@tanstack/react-router", () => ({
  createFileRoute: () => (options: unknown) => options,
  Link: ({ children, to }: { children: React.ReactNode; to: string }) =>
    createElement("a", { href: to }, children),
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    user: {
      userId: "user-1",
      username: "store.manager",
      email: "manager@example.com",
      role: "manager",
      permissions: state.permissions,
    },
    can: (permission: string) => state.permissions.includes(permission),
  }),
}));

vi.mock("@/lib/store", () => ({
  useStore: () => ({ theme: state.theme, setTheme: state.setTheme }),
}));

vi.mock("@/components/app/product-management", () => ({
  ProductManagement: () => createElement("div", null, "Product management"),
}));
vi.mock("@/components/app/user-management", () => ({
  UserManagement: () => createElement("div", null, "User management"),
}));
vi.mock("@/components/app/notification-deliveries", () => ({
  NotificationDeliveries: () => createElement("div", null, "Email delivery history"),
}));

import { SettingsPage } from "./_console.settings";

function render() {
  return renderToStaticMarkup(createElement(SettingsPage));
}

describe("SettingsPage", () => {
  beforeEach(() => {
    state.permissions = [];
    state.theme = "dark";
    state.setTheme.mockReset();
  });

  it("keeps the four personal settings sections and existing camera route available", () => {
    const html = render();

    expect(html).toContain("My Account");
    expect(html).toContain("Security");
    expect(html).toContain("Appearance");
    expect(html).toContain("Notification Preferences");
    expect(html).toContain('href="/shelves"');
    expect(html).toContain("Self-service password changes");
    expect(html).toContain('aria-pressed="true"');
  });

  it("shows additional settings tabs only with their existing permissions", () => {
    state.permissions = ["products.read"];
    let html = render();
    expect(html).toContain(">Products</button>");
    expect(html).not.toContain(">Users &amp; access</button>");
    expect(html).not.toContain(">Email delivery</button>");

    state.permissions = ["products.read", "users.read", "settings.read"];
    html = render();
    expect(html).toContain(">Products</button>");
    expect(html).toContain(">Users &amp; access</button>");
    expect(html).toContain(">Email delivery</button>");
  });
});
