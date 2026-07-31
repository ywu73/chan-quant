import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { startQuotePolling, type VisibilitySource } from "./quotePolling";
import type { QuoteSnapshot } from "./types/quote";


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
  quote_at: "2026-07-31T14:35:06+08:00",
  received_at: "2026-07-31T14:35:07+08:00",
  source: "sina-undocumented-quote",
  status: "LIVE",
  is_stale: false,
} satisfies QuoteSnapshot;


describe("quote polling lifecycle", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("polls while visible and pauses while hidden", async () => {
    const visibility = new FakeVisibility();
    const fetchQuote = vi.fn().mockResolvedValue(quote);
    const onQuote = vi.fn();

    const stop = startQuotePolling({
      symbol: "000001.SZ",
      fetchQuote,
      onQuote,
      onError: vi.fn(),
      visibilitySource: visibility,
      intervalMs: 8_000,
    });
    await Promise.resolve();
    await Promise.resolve();

    expect(fetchQuote).toHaveBeenCalledTimes(1);
    expect(onQuote).toHaveBeenCalledWith(quote);

    await vi.advanceTimersByTimeAsync(8_000);
    expect(fetchQuote).toHaveBeenCalledTimes(2);

    visibility.setVisibility("hidden");
    await vi.advanceTimersByTimeAsync(24_000);
    expect(fetchQuote).toHaveBeenCalledTimes(2);

    visibility.setVisibility("visible");
    await Promise.resolve();
    await Promise.resolve();
    expect(fetchQuote).toHaveBeenCalledTimes(3);

    stop();
    await vi.advanceTimersByTimeAsync(24_000);
    expect(fetchQuote).toHaveBeenCalledTimes(3);
  });
});
