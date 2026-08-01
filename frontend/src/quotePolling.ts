import type { QuoteSnapshot } from "./types/quote";
import { startVisiblePolling, type VisibilitySource } from "./visiblePolling";


export type { VisibilitySource } from "./visiblePolling";

interface QuotePollingOptions {
  symbol: string;
  fetchQuote: (symbol: string, signal?: AbortSignal) => Promise<QuoteSnapshot>;
  onQuote: (quote: QuoteSnapshot) => void;
  onError: (error: unknown) => void;
  visibilitySource: VisibilitySource;
  intervalMs?: number;
}


export function startQuotePolling({
  symbol,
  fetchQuote,
  onQuote,
  onError,
  visibilitySource,
  intervalMs = 8_000,
}: QuotePollingOptions): () => void {
  return startVisiblePolling({
    visibilitySource,
    intervalMs,
    poll: async (signal) => {
      try {
        const quote = await fetchQuote(symbol, signal);
        if (!signal.aborted) {
          onQuote(quote);
        }
      } catch (error) {
        if (!signal.aborted) {
          onError(error);
        }
      }
    },
  });
}
