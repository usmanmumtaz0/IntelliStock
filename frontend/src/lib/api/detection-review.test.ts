import { afterEach, expect, it, vi } from "vitest";
import { api } from "./index";

afterEach(() => vi.unstubAllGlobals());
it("deletes only the selected detection using its encoded identifier", async () => {
  const fetcher = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ deleted_id: "id/one", inventory_effect: "none" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fetcher);
  const result = await api.deleteDetection("id/one");
  expect(fetcher.mock.calls[0]?.[0]).toContain("/video-jobs/detections/id%2Fone");
  expect(fetcher.mock.calls[0]?.[1].method).toBe("DELETE");
  expect(result.inventory_effect).toBe("none");
});
