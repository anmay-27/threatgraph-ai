import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";
afterEach(() => vi.unstubAllGlobals());
describe("API client", () => {
  it("returns real JSON payloads", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "case" }))),
    );
    expect(await api("/history")).toEqual({ id: "case" });
  });
  it("surfaces useful API failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({ detail: "Upload exceeds size limit" }),
            { status: 413 },
          ),
        ),
    );
    await expect(api("/analyze/file")).rejects.toThrow(
      "Upload exceeds size limit",
    );
  });
  it("handles non-JSON gateway errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("Bad gateway", { status: 502 })),
    );
    await expect(api("/health")).rejects.toThrow("Server did not respond");
  });
});
