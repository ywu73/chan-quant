import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchMarketBreadth } from "./marketBreadth";


afterEach(() => vi.unstubAllGlobals());


describe("market breadth API client", () => {
  it("loads the fixed audited Shanghai and Shenzhen A-share contract", async () => {
    const payload = { status: "COMPLETE", market: "CN_A_SH_SZ_V1" };
    const request = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", request);
    const controller = new AbortController();

    await expect(fetchMarketBreadth(controller.signal)).resolves.toEqual(payload);
    expect(request).toHaveBeenCalledWith(
      "/api/v1/market-breadth?market=CN_A_SH_SZ_V1",
      { signal: controller.signal },
    );
  });


  it("surfaces a structured fail-closed rejection", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: {
              status: "REJECTED",
              code: "QUOTES_HASH_MISMATCH",
              message: "quotes.csv hash does not match manifest",
            },
          }),
          { status: 422, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    await expect(fetchMarketBreadth()).rejects.toThrow(
      "市场温度不可用（HTTP 422）：quotes.csv hash does not match manifest [QUOTES_HASH_MISMATCH]",
    );
  });
});
