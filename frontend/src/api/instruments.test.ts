import { afterEach, describe, expect, it, vi } from "vitest";

import { resolveInstrument, searchInstruments } from "./instruments";


afterEach(() => vi.unstubAllGlobals());


describe("instrument search API client", () => {
  it("resolves a canonical symbol through the backend identity contract", async () => {
    const identity = {
      symbol: "513100.SH",
      name: "纳指ETF国泰",
      exchange: "SH" as const,
      asset_type: "ETF" as const,
      price_precision: 3,
    };
    const request = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(identity), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", request);
    const controller = new AbortController();

    await expect(resolveInstrument(" 513100.sh ", controller.signal)).resolves.toEqual(identity);
    expect(request).toHaveBeenCalledWith(
      "/api/v1/instruments/513100.SH",
      { signal: controller.signal },
    );
  });

  it("encodes the query and forwards cancellation", async () => {
    const payload = {
      query: "平安 银行",
      items: [
        {
          symbol: "000001.SZ",
          name: "平安银行",
          exchange: "SZ",
          asset_type: "UNKNOWN",
          price_precision: 2,
        },
      ],
      source: "sina-undocumented-suggest",
      limit: 5,
    };
    const request = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", request);
    const controller = new AbortController();

    await expect(searchInstruments(" 平安 银行 ", controller.signal, 5)).resolves.toEqual(payload);
    expect(request).toHaveBeenCalledWith(
      "/api/v1/instruments/search?q=%E5%B9%B3%E5%AE%89%20%E9%93%B6%E8%A1%8C&limit=5",
      { signal: controller.signal },
    );
  });

  it("surfaces the classified backend failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Sina suggest request returned HTTP 403" }), {
          status: 502,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(searchInstruments("平安")).rejects.toThrow(
      "证券搜索不可用（HTTP 502）：Sina suggest request returned HTTP 403",
    );
  });
});
