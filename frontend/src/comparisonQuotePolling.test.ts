import { describe, expect, it, vi } from "vitest";

import {
  startComparisonQuotePolling,
  type ComparisonQuoteUpdate,
} from "./comparisonQuotePolling";
import type { VisibilitySource } from "./quotePolling";
import type { QuoteBatch, QuoteSnapshot } from "./types/quote";


class FakeVisibility implements VisibilitySource {
  visibilityState: "visible" | "hidden" = "visible";
  private listeners = new Set<() => void>();

  addEventListener(_type: "visibilitychange", listener: () => void) {
    this.listeners.add(listener);
  }

  removeEventListener(_type: "visibilitychange", listener: () => void) {
    this.listeners.delete(listener);
  }

  setVisibility(state: "visible" | "hidden") {
    this.visibilityState = state;
    this.listeners.forEach((listener) => listener());
  }
}


const quote = {
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
  quote_at: "2026-08-01T14:35:06+08:00",
  received_at: "2026-08-01T14:35:07+08:00",
  source: "sina-undocumented-quote",
  status: "LIVE",
  is_stale: false,
} satisfies QuoteSnapshot;


function completeBatch(): QuoteBatch {
  return {
    status: "COMPLETE",
    requested: [quote.symbol],
    succeeded: 1,
    failed: 0,
    quotes: [quote],
    failures: [],
    source: "sina-undocumented-batch-quote",
  };
}


describe("comparison quote polling", () => {
  it("publishes successful and failed symbols independently", async () => {
    const visibility = new FakeVisibility();
    const fetchQuotes = vi.fn((_symbols: string[], _signal?: AbortSignal) => Promise.resolve({
      status: "PARTIAL",
      requested: [quote.symbol, "600000.SH"],
      succeeded: 1,
      failed: 1,
      quotes: [quote],
      failures: [{
        symbol: "600000.SH",
        code: "QUOTE_UNAVAILABLE",
        message: "测试行情不可用",
      }],
      source: "sina-undocumented-batch-quote",
    } satisfies QuoteBatch));
    const updates: Array<[string, ComparisonQuoteUpdate]> = [];

    const stop = startComparisonQuotePolling({
      symbols: [quote.symbol, "600000.SH"],
      fetchQuotes,
      onUpdate: (symbol, update) => updates.push([symbol, update]),
      visibilitySource: visibility,
      intervalMs: 60_000,
    });

    await vi.waitFor(() => expect(updates).toHaveLength(2));
    expect(updates).toEqual([
      [quote.symbol, { status: "READY", quote, error: null }],
      ["600000.SH", {
        status: "ERROR",
        quote: null,
        error: "测试行情不可用 [QUOTE_UNAVAILABLE]",
      }],
    ]);
    expect(fetchQuotes).toHaveBeenCalledOnce();
    expect(fetchQuotes.mock.calls[0][0]).toEqual([quote.symbol, "600000.SH"]);

    stop();
  });

  it("aborts in-flight work and suppresses late updates after stop", async () => {
    const visibility = new FakeVisibility();
    let requestSignal: AbortSignal | undefined;
    let resolveRequest: ((value: QuoteBatch) => void) | undefined;
    const fetchQuotes = vi.fn((_symbols: string[], signal?: AbortSignal) => {
      requestSignal = signal;
      return new Promise<QuoteBatch>((resolve) => {
        resolveRequest = resolve;
      });
    });
    const onUpdate = vi.fn();

    const stop = startComparisonQuotePolling({
      symbols: [quote.symbol],
      fetchQuotes,
      onUpdate,
      visibilitySource: visibility,
    });
    await vi.waitFor(() => expect(fetchQuotes).toHaveBeenCalledOnce());

    stop();
    expect(requestSignal?.aborted).toBe(true);
    resolveRequest?.(completeBatch());
    await Promise.resolve();
    await Promise.resolve();
    expect(onUpdate).not.toHaveBeenCalled();
  });

  it("aborts while hidden and starts a fresh cycle when visible again", async () => {
    const visibility = new FakeVisibility();
    const signals: AbortSignal[] = [];
    const resolvers: Array<(value: QuoteBatch) => void> = [];
    const fetchQuotes = vi.fn((_symbols: string[], signal?: AbortSignal) => {
      if (signal) signals.push(signal);
      return new Promise<QuoteBatch>((resolve) => resolvers.push(resolve));
    });
    const onUpdate = vi.fn();

    const stop = startComparisonQuotePolling({
      symbols: [quote.symbol],
      fetchQuotes,
      onUpdate,
      visibilitySource: visibility,
    });
    await vi.waitFor(() => expect(fetchQuotes).toHaveBeenCalledTimes(1));

    visibility.setVisibility("hidden");
    expect(signals[0].aborted).toBe(true);
    visibility.setVisibility("visible");
    await vi.waitFor(() => expect(fetchQuotes).toHaveBeenCalledTimes(2));

    resolvers[1](completeBatch());
    await vi.waitFor(() => expect(onUpdate).toHaveBeenCalledOnce());
    resolvers[0](completeBatch());
    await Promise.resolve();
    await Promise.resolve();
    expect(onUpdate).toHaveBeenCalledOnce();

    stop();
  });

  it("publishes a whole-batch failure to every requested symbol", async () => {
    const visibility = new FakeVisibility();
    const onUpdate = vi.fn();
    const fetchQuotes = vi.fn().mockRejectedValue(new Error("批量协议不可用"));

    const stop = startComparisonQuotePolling({
      symbols: [quote.symbol, "600000.SH"],
      fetchQuotes,
      onUpdate,
      visibilitySource: visibility,
      intervalMs: 60_000,
    });

    await vi.waitFor(() => expect(onUpdate).toHaveBeenCalledTimes(2));
    expect(onUpdate).toHaveBeenNthCalledWith(1, quote.symbol, {
      status: "ERROR",
      quote: null,
      error: "批量协议不可用",
    });
    expect(onUpdate).toHaveBeenNthCalledWith(2, "600000.SH", {
      status: "ERROR",
      quote: null,
      error: "批量协议不可用",
    });

    stop();
  });
});
