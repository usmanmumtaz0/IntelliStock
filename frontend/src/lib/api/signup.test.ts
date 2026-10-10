import { afterEach, expect, it, vi } from "vitest";
import { api } from "./index";
import { operations } from "./operations";

afterEach(() => vi.unstubAllGlobals());

it("public signup sends identity and password but no role or activation", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValue(
      new Response(JSON.stringify({ message: "Pending approval" }), { status: 202 }),
    );
  vi.stubGlobal("fetch", fetchMock);
  const result = await api.signup("person@example.com", "person", "test-password-long");
  expect(result.message).toBe("Pending approval");
  const [url, init] = fetchMock.mock.calls[0]!;
  expect(url).toContain("/auth/signup");
  expect(JSON.parse(init.body)).toEqual({
    email: "person@example.com",
    username: "person",
    password: "test-password-long",
  });
});

it("approval uses the dedicated endpoint without a requested elevated role", async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  await operations.approveSignup("user-123");
  const [url, init] = fetchMock.mock.calls[0]!;
  expect(url).toContain("/users/user-123/approve");
  expect(init.method).toBe("POST");
  expect(init.body).toBeUndefined();
});
