import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { SidePerformance } from "../types/dashboard";
import { PerformanceCard } from "./PerformanceCard";


const performance = {
  side: "BUY",
  total_signals: 2,
  horizons: [
    { bars: 5, eligible: 2, successes: 1, success_rate: 0.5, mean_forward_return: 0.01 },
    { bars: 10, eligible: 2, successes: 1, success_rate: 0.5, mean_forward_return: -0.02 },
    { bars: 20, eligible: 0, successes: 0, success_rate: 0, mean_forward_return: 0 },
  ],
  recent_signal_dates: ["2026-08-01"],
} satisfies SidePerformance;


describe("PerformanceCard", () => {
  it("colors signed forward returns independently of the signal side", () => {
    const markup = renderToStaticMarkup(<PerformanceCard performance={performance} />);

    expect(markup).toContain("performance-card--buy");
    expect(markup).toContain("performance-row__return market-value market-value--up");
    expect(markup).toContain("performance-row__return market-value market-value--down");
    expect(markup).toContain("performance-row__return market-value market-value--neutral");
  });
});
