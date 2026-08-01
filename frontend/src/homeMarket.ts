import type { QuoteSnapshot } from "./types/quote";


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


export const HOME_MARKET_INSTRUMENTS: MarketInstrument[] = [
  { symbol: "000001.SH", displayName: "上证指数", color: "red" },
  { symbol: "000300.SH", displayName: "沪深300", color: "blue" },
  { symbol: "000016.SH", displayName: "上证50", color: "orange" },
  { symbol: "399006.SZ", displayName: "创业板指", color: "green" },
  { symbol: "000688.SH", displayName: "科创50", color: "purple" },
];


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
