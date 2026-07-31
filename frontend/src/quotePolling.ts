import type { QuoteSnapshot } from "./types/quote";


export interface VisibilitySource {
  readonly visibilityState: "visible" | "hidden";
  addEventListener(type: "visibilitychange", listener: () => void): void;
  removeEventListener(type: "visibilitychange", listener: () => void): void;
}

interface QuotePollingOptions {
  symbol: string;
  fetchQuote: (symbol: string) => Promise<QuoteSnapshot>;
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
  let stopped = false;
  let inFlight = false;
  let timer: ReturnType<typeof setTimeout> | undefined;

  const clearTimer = () => {
    if (timer !== undefined) {
      clearTimeout(timer);
      timer = undefined;
    }
  };

  const schedule = () => {
    clearTimer();
    if (!stopped && visibilitySource.visibilityState === "visible") {
      timer = setTimeout(() => void poll(), intervalMs);
    }
  };

  const poll = async () => {
    if (stopped || inFlight || visibilitySource.visibilityState !== "visible") {
      return;
    }
    inFlight = true;
    try {
      const quote = await fetchQuote(symbol);
      if (!stopped) {
        onQuote(quote);
      }
    } catch (error) {
      if (!stopped) {
        onError(error);
      }
    } finally {
      inFlight = false;
      schedule();
    }
  };

  const handleVisibility = () => {
    clearTimer();
    if (visibilitySource.visibilityState === "visible") {
      void poll();
    }
  };

  visibilitySource.addEventListener("visibilitychange", handleVisibility);
  void poll();

  return () => {
    stopped = true;
    clearTimer();
    visibilitySource.removeEventListener("visibilitychange", handleVisibility);
  };
}
