import { useEffect, useState } from "react";

import { fetchQuote } from "./api/quote";
import {
  startComparisonQuotePolling,
  type ComparisonQuoteState,
} from "./comparisonQuotePolling";


function loadingStates(symbols: string[]): Record<string, ComparisonQuoteState> {
  return Object.fromEntries(symbols.map((symbol) => [
    symbol,
    { status: "LOADING", quote: null, error: null },
  ]));
}


export function useComparisonQuotes(
  symbols: string[],
): Record<string, ComparisonQuoteState> {
  const symbolKey = symbols.join("|");
  const [states, setStates] = useState<Record<string, ComparisonQuoteState>>(
    () => loadingStates(symbols),
  );

  useEffect(() => {
    const currentSymbols = symbolKey ? symbolKey.split("|") : [];
    setStates(loadingStates(currentSymbols));
    if (currentSymbols.length === 0) return;

    return startComparisonQuotePolling({
      symbols: currentSymbols,
      fetchQuote,
      onUpdate: (symbol, update) => {
        setStates((current) => ({ ...current, [symbol]: update }));
      },
      visibilitySource: document,
      intervalMs: 8_000,
    });
  }, [symbolKey]);

  return states;
}
