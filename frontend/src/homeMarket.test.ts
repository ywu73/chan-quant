import { describe, expect, it, vi } from "vitest";

import {
  HOME_MARKET_INSTRUMENTS,
  intradayRangePosition,
  loadMarketQuotes,
} from "./homeMarket";
import { CN_BROAD_INDEX_CATALOG } from "./marketInstruments";
import type { QuoteSnapshot } from "./types/quote";


const quote = {
  symbol: "000001.SH",
  name: "上证指数",
  last_price: 3625,
  previous_close: 3600,
  change: 25,
  change_percent: 0.006944,
  open: 3590,
  high: 3650,
  low: 3550,
  volume: 1_200_000,
  quote_at: "2026-08-01T15:00:00+08:00",
  received_at: "2026-08-01T15:00:01+08:00",
  source: "sina-undocumented-quote",
  status: "CLOSED",
  is_stale: false,
} satisfies QuoteSnapshot;


describe("home market snapshot", () => {
  it("uses every verified broad index identity with a distinct accent", () => {
    expect(HOME_MARKET_INSTRUMENTS.map(({ symbol, displayName }) => ({
      symbol,
      displayName,
    }))).toEqual(CN_BROAD_INDEX_CATALOG.map((instrument) => ({
      symbol: instrument.symbol,
      displayName: instrument.name,
    })));
    expect(
      new Set(HOME_MARKET_INSTRUMENTS.map((instrument) => instrument.color)).size,
    ).toBe(8);
  });

  it("keeps seven successful cards when one of eight quotes fails", async () => {
    const failedSymbol = "000905.SH";
    const fetcher = vi.fn(async (symbol: string) => {
      if (symbol === failedSymbol) throw new Error("provider unavailable");
      const instrument = HOME_MARKET_INSTRUMENTS.find((item) => item.symbol === symbol);
      if (!instrument) throw new Error(`unexpected instrument ${symbol}`);
      return { ...quote, symbol, name: instrument.displayName };
    });

    const results = await loadMarketQuotes(HOME_MARKET_INSTRUMENTS, fetcher);

    expect(results).toHaveLength(8);
    expect(results.filter((result) => result.quote !== null)).toHaveLength(7);
    expect(results.find((result) => result.instrument.symbol === failedSymbol)).toMatchObject({
      quote: null,
      error: "provider unavailable",
    });
  });

  it("locates the latest price within the observed intraday range", () => {
    expect(intradayRangePosition(quote)).toBe(75);
    expect(intradayRangePosition({ ...quote, high: 3600, low: 3600 })).toBe(50);
  });
});
