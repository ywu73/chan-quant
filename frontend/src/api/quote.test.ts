import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchQuote, fetchQuotes } from "./quote";


afterEach(() => vi.unstubAllGlobals());


describe("quote API client", () => {
  it("loads the independent quote endpoint", async () => {
    const payload = {
      symbol: "000001.SZ",
      name: "平安银行",
      last_price: 11.62,
      previous_close: 11.48,
      change: 0.14,
      change_percent: 0.012195,
      open: 11.48,
      high: 11.67,
      low: 11.42,
      volume: 63_210_000,
      quote_at: "2026-07-31T14:35:06+08:00",
      received_at: "2026-07-31T14:35:07+08:00",
      source: "sina-undocumented-quote",
      status: "LIVE",
      is_stale: false,
    };
    const request = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", request);

    await expect(fetchQuote("000001.SZ")).resolves.toEqual(payload);
    expect(request).toHaveBeenCalledWith("/api/v1/instruments/000001.SZ/quote");
  });

  it("surfaces the classified backend failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Sina returned no current quote" }), {
          status: 503,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(fetchQuote("000001.SZ")).rejects.toThrow(
      "实时行情不可用（HTTP 503）：Sina returned no current quote",
    );
  });

  it("surfaces a structured remote-network rejection", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({
          detail: {
            code: "REMOTE_NETWORK_DISABLED",
            message: "remote market access is disabled",
          },
        }), {
          status: 503,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(fetchQuote("000001.SZ")).rejects.toThrow(
      "实时行情不可用（HTTP 503）：remote market access is disabled [REMOTE_NETWORK_DISABLED]",
    );
  });

  it("loads one batch quote request with repeated canonical symbols", async () => {
    const payload = {
      status: "FAILED",
      requested: ["000001.SZ", "600000.SH"],
      succeeded: 0,
      failed: 2,
      quotes: [],
      failures: [
        {
          symbol: "000001.SZ",
          code: "QUOTE_UNAVAILABLE",
          message: "测试行情不可用",
        },
        {
          symbol: "600000.SH",
          code: "QUOTE_UNAVAILABLE",
          message: "测试行情不可用",
        },
      ],
      source: "sina-undocumented-batch-quote",
    };
    const request = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", request);
    const controller = new AbortController();

    await expect(
      fetchQuotes(["000001.SZ", "600000.SH"], controller.signal),
    ).resolves.toEqual(payload);
    expect(request).toHaveBeenCalledWith(
      "/api/v1/quotes?symbols=000001.SZ&symbols=600000.SH",
      { signal: controller.signal },
    );
  });

  it("surfaces a whole-batch backend failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Sina batch response invalid" }), {
          status: 502,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(fetchQuotes(["000001.SZ"])).rejects.toThrow(
      "批量实时行情不可用（HTTP 502）：Sina batch response invalid",
    );
  });
});
