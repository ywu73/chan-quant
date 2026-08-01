import type { VisibilitySource } from "./quotePolling";
import type { QuoteSnapshot } from "./types/quote";


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
  let stopped = false;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let activeController: AbortController | undefined;

  const clearTimer = () => {
    if (timer !== undefined) {
      clearTimeout(timer);
      timer = undefined;
    }
  };

  const poll = async () => {
    if (stopped || visibilitySource.visibilityState !== "visible") return;
    const controller = new AbortController();
    activeController = controller;
    await Promise.all(symbols.map(async (symbol) => {
      try {
        const quote = await fetchQuote(symbol, controller.signal);
        if (!stopped && !controller.signal.aborted) {
          onUpdate(symbol, { status: "READY", quote, error: null });
        }
      } catch (reason) {
        if (!stopped && !controller.signal.aborted) {
          onUpdate(symbol, { status: "ERROR", quote: null, error: errorMessage(reason) });
        }
      }
    }));
    if (activeController === controller) activeController = undefined;
    if (!stopped && visibilitySource.visibilityState === "visible") {
      timer = setTimeout(() => void poll(), intervalMs);
    }
  };

  const handleVisibility = () => {
    clearTimer();
    if (visibilitySource.visibilityState === "hidden") {
      activeController?.abort();
      activeController = undefined;
      return;
    }
    void poll();
  };

  visibilitySource.addEventListener("visibilitychange", handleVisibility);
  void poll();

  return () => {
    stopped = true;
    activeController?.abort();
    activeController = undefined;
    clearTimer();
    visibilitySource.removeEventListener("visibilitychange", handleVisibility);
  };
}
