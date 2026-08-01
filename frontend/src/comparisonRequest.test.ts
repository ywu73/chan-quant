import { describe, expect, it, vi } from "vitest";

import type { MarketComparison } from "./types/comparison";
import { createComparisonRequestRunner } from "./comparisonRequest";


const RESULT = { status: "COMPLETE" } as MarketComparison;


describe("comparison request runner", () => {
  it("aborts and suppresses a stale result after the selection changes", async () => {
    let resolveFirst: (value: MarketComparison) => void = () => undefined;
    const signals: AbortSignal[] = [];
    const fetcher = vi.fn()
      .mockImplementationOnce((_symbols, _range, signal: AbortSignal) => {
        signals.push(signal);
        return new Promise<MarketComparison>((resolve) => { resolveFirst = resolve; });
      })
      .mockImplementationOnce((_symbols, _range, signal: AbortSignal) => {
        signals.push(signal);
        return Promise.resolve(RESULT);
      });
    const staleSuccess = vi.fn();
    const currentSuccess = vi.fn();
    const runner = createComparisonRequestRunner(fetcher);

    runner.run(["000001.SH", "399001.SZ"], {}, { success: staleSuccess });
    runner.run(["000300.SH", "000905.SH"], {}, { success: currentSuccess });
    resolveFirst(RESULT);
    await Promise.resolve();
    await Promise.resolve();

    expect(signals[0].aborted).toBe(true);
    expect(signals[1].aborted).toBe(false);
    expect(staleSuccess).not.toHaveBeenCalled();
    expect(currentSuccess).toHaveBeenCalledWith(RESULT);
  });
});
