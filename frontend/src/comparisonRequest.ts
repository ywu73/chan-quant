import type { MarketComparison } from "./types/comparison";


interface ComparisonRange {
  start?: string;
  end?: string;
}

type ComparisonFetcher = (
  symbols: string[],
  range: ComparisonRange,
  signal: AbortSignal,
) => Promise<MarketComparison>;

interface ComparisonRequestObserver {
  success?(result: MarketComparison): void;
  failure?(reason: unknown): void;
  settled?(): void;
}


export function createComparisonRequestRunner(fetchComparison: ComparisonFetcher) {
  let active: AbortController | null = null;

  const invalidate = () => {
    active?.abort();
    active = null;
  };

  return {
    run(
      symbols: string[],
      range: ComparisonRange,
      observer: ComparisonRequestObserver,
    ): void {
      invalidate();
      const controller = new AbortController();
      active = controller;
      fetchComparison(symbols, range, controller.signal)
        .then((result) => {
          if (active === controller && !controller.signal.aborted) observer.success?.(result);
        })
        .catch((reason: unknown) => {
          if (active === controller && !controller.signal.aborted) observer.failure?.(reason);
        })
        .finally(() => {
          if (active !== controller || controller.signal.aborted) return;
          active = null;
          observer.settled?.();
        });
    },
    invalidate,
  };
}
