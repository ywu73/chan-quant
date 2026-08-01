import type { QuoteSnapshot } from "./types/quote";
import { CN_BROAD_INDEX_BY_SYMBOL } from "./marketInstruments";


export interface MarketInstrument {
  symbol: string;
  displayName: string;
  color: "red" | "blue" | "orange" | "green" | "purple";
}


export interface MarketQuoteResult {
  instrument: MarketInstrument;
  quote: QuoteSnapshot | null;
  error: string | null;
}


const HOME_MARKET_COLORS: Array<[string, MarketInstrument["color"]]> = [
  ["000001.SH", "red"],
  ["000300.SH", "blue"],
  ["000016.SH", "orange"],
  ["399006.SZ", "green"],
  ["000688.SH", "purple"],
];

export const HOME_MARKET_INSTRUMENTS: MarketInstrument[] = HOME_MARKET_COLORS.map(
  ([symbol, color]) => {
    const identity = CN_BROAD_INDEX_BY_SYMBOL.get(symbol);
    if (!identity) throw new Error(`missing shared market identity for ${symbol}`);
    return { symbol, displayName: identity.name, color };
  },
);


export async function loadMarketQuotes(
  instruments: MarketInstrument[],
  fetcher: (symbol: string, signal?: AbortSignal) => Promise<QuoteSnapshot>,
  signal?: AbortSignal,
): Promise<MarketQuoteResult[]> {
  const settled = await Promise.allSettled(
    instruments.map((instrument) => fetcher(instrument.symbol, signal)),
  );

  return settled.map((result, index) => {
    const instrument = instruments[index];
    if (result.status === "fulfilled") {
      return { instrument, quote: result.value, error: null };
    }
    const error = result.reason instanceof Error
      ? result.reason.message
      : "行情快照不可用";
    return { instrument, quote: null, error };
  });
}


export function intradayRangePosition(quote: QuoteSnapshot): number {
  const span = quote.high - quote.low;
  if (!Number.isFinite(span) || span <= 0) {
    return 50;
  }
  return Math.min(100, Math.max(0, ((quote.last_price - quote.low) / span) * 100));
}
