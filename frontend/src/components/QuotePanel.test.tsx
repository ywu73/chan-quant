import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { QuoteSnapshot } from "../types/quote";
import { QuotePanel } from "./QuotePanel";


const quote = {
  symbol: "000001.SZ",
  name: "平安银行",
  last_price: 11.48,
  previous_close: 11.48,
  change: 0,
  change_percent: 0,
  open: 11.48,
  high: 11.48,
  low: 11.48,
  volume: 1_000,
  quote_at: "2026-08-04T15:00:00+08:00",
  received_at: "2026-08-04T15:00:01+08:00",
  source: "sina-undocumented-quote",
  status: "CLOSED",
  is_stale: false,
} satisfies QuoteSnapshot;


describe("QuotePanel", () => {
  it("renders positive, negative, and flat changes with distinct market tones", () => {
    const renderChange = (change: number) => renderToStaticMarkup(
      <QuotePanel
        symbol={quote.symbol}
        instrumentName={quote.name}
        pricePrecision={2}
        strategyAsOf="2026-08-04"
        quote={{ ...quote, change, change_percent: change / quote.previous_close }}
        error={null}
      />,
    );

    expect(renderChange(0.1)).toContain("quote-change--up");
    expect(renderChange(-0.1)).toContain("quote-change--down");
    expect(renderChange(0)).toContain("quote-change--neutral");
  });
});
