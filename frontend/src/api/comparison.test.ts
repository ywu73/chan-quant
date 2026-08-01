import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchMarketComparison } from "./comparison";


afterEach(() => vi.unstubAllGlobals());


describe("market comparison API client", () => {
  it("sends distinct symbols, date range, and cancellation as repeated query parameters", async () => {
    const payload = {
      status: "COMPLETE",
      requested: ["000001.SZ", "600000.SH"],
      succeeded: 2,
      failed: 0,
      requested_from: "2026-01-01",
      requested_to: "2026-01-31",
      common_from: "2026-01-02",
      common_to: "2026-01-30",
      dates: ["2026-01-02", "2026-01-03"],
      series: [],
      failures: [],
    };
    const request = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", request);
    const controller = new AbortController();

    await expect(fetchMarketComparison(
      ["000001.SZ", "600000.SH"],
      { start: "2026-01-01", end: "2026-01-31" },
      controller.signal,
    )).resolves.toEqual(payload);

    expect(request).toHaveBeenCalledWith(
      "/api/v1/market-comparison?symbols=000001.SZ&symbols=600000.SH&start=2026-01-01&end=2026-01-31",
      { signal: controller.signal },
    );
  });

  it("surfaces a classified backend contract failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "comparison requires 2 to 8 symbols" }), {
          status: 422,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(fetchMarketComparison(["000001.SZ"])).rejects.toThrow(
      "读取走势对比失败（HTTP 422）：comparison requires 2 to 8 symbols",
    );
  });
});
