import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchDashboard } from "./dashboard";


afterEach(() => vi.unstubAllGlobals());


describe("dashboard API client", () => {
  it("surfaces structured market snapshot rejection reason codes", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: {
              status: "REJECTED",
              code: "HASH_MISMATCH",
              message: "bars.csv SHA-256 does not match manifest",
            },
          }),
          { status: 422, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    await expect(fetchDashboard("000001.SZ")).rejects.toThrow(
      "读取策略快照失败（HTTP 422）：数据快照已拒绝 [HASH_MISMATCH] "
      + "bars.csv SHA-256 does not match manifest",
    );
  });

  it("preserves existing string error details", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "expected at least 92 bars, got 91" }), {
          status: 422,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(fetchDashboard("000001.SZ")).rejects.toThrow(
      "读取策略快照失败（HTTP 422）：expected at least 92 bars, got 91",
    );
  });
});
