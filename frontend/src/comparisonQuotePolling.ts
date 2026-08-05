import type { QuoteBatch, QuoteFailure, QuoteSnapshot } from "./types/quote";
import { startVisiblePolling, type VisibilitySource } from "./visiblePolling";


export type ComparisonQuoteUpdate =
  | { status: "READY"; quote: QuoteSnapshot; error: null }
  | { status: "ERROR"; quote: null; error: string };

export type ComparisonQuoteState =
  | { status: "LOADING"; quote: null; error: null }
  | ComparisonQuoteUpdate;

interface ComparisonQuotePollingOptions {
  symbols: string[];
  fetchQuotes: (symbols: string[], signal?: AbortSignal) => Promise<QuoteBatch>;
  onUpdate: (symbol: string, update: ComparisonQuoteUpdate) => void;
  visibilitySource: VisibilitySource;
  intervalMs?: number;
}


function errorMessage(reason: unknown): string {
  return reason instanceof Error ? reason.message : "实时行情不可用";
}


function failureMessage(failure: QuoteFailure): string {
  return `${failure.message} [${failure.code}]`;
}


export function startComparisonQuotePolling({
  symbols,
  fetchQuotes,
  onUpdate,
  visibilitySource,
  intervalMs = 8_000,
}: ComparisonQuotePollingOptions): () => void {
  return startVisiblePolling({
    visibilitySource,
    intervalMs,
    poll: async (signal) => {
      try {
        const batch = await fetchQuotes(symbols, signal);
        if (signal.aborted) return;

        const quotes = new Map(batch.quotes.map((quote) => [quote.symbol, quote]));
        const failures = new Map(batch.failures.map((failure) => [failure.symbol, failure]));
        symbols.forEach((symbol) => {
          const quote = quotes.get(symbol);
          if (quote) {
            onUpdate(symbol, { status: "READY", quote, error: null });
            return;
          }
          const failure = failures.get(symbol);
          onUpdate(symbol, {
            status: "ERROR",
            quote: null,
            error: failure
              ? failureMessage(failure)
              : "批量实时行情响应缺少该标的 [BATCH_QUOTE_ITEM_MISSING]",
          });
        });
      } catch (reason) {
        if (signal.aborted) return;
        const message = errorMessage(reason);
        symbols.forEach((symbol) => {
          onUpdate(symbol, { status: "ERROR", quote: null, error: message });
        });
      }
    },
  });
}
