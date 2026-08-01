import type { QuoteSnapshot } from "./types/quote";
import { startVisiblePolling, type VisibilitySource } from "./visiblePolling";


export type ComparisonQuoteUpdate =
  | { status: "READY"; quote: QuoteSnapshot; error: null }
  | { status: "ERROR"; quote: null; error: string };

export type ComparisonQuoteState =
  | { status: "LOADING"; quote: null; error: null }
  | ComparisonQuoteUpdate;

interface ComparisonQuotePollingOptions {
  symbols: string[];
  fetchQuote: (symbol: string, signal?: AbortSignal) => Promise<QuoteSnapshot>;
  onUpdate: (symbol: string, update: ComparisonQuoteUpdate) => void;
  visibilitySource: VisibilitySource;
  intervalMs?: number;
}


function errorMessage(reason: unknown): string {
  return reason instanceof Error ? reason.message : "实时行情不可用";
}


export function startComparisonQuotePolling({
  symbols,
  fetchQuote,
  onUpdate,
  visibilitySource,
  intervalMs = 8_000,
}: ComparisonQuotePollingOptions): () => void {
  return startVisiblePolling({
    visibilitySource,
    intervalMs,
    poll: async (signal) => {
      await Promise.all(symbols.map(async (symbol) => {
        try {
          const quote = await fetchQuote(symbol, signal);
          if (!signal.aborted) {
            onUpdate(symbol, { status: "READY", quote, error: null });
          }
        } catch (reason) {
          if (!signal.aborted) {
            onUpdate(symbol, { status: "ERROR", quote: null, error: errorMessage(reason) });
          }
        }
      }));
    },
  });
}
