import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { ComparisonQuoteState } from "../comparisonQuotePolling";
import type { MarketInstrument } from "../homeMarket";
import type { ComparisonSeries } from "../types/comparison";
import type { QuoteSnapshot } from "../types/quote";
import { IndexPerformanceCard } from "./IndexPerformanceCard";


const instrument = {
  symbol: "000001.SH",
  displayName: "上证指数",
  color: "red",
} satisfies MarketInstrument;

const series = {
  instrument: {
    symbol: "000001.SH",
    name: "上证指数",
    exchange: "SH",
    asset_type: "UNKNOWN",
    price_precision: 2,
  },
  data_source: "sina-undocumented-kline",
  adjustment: "unspecified",
  currency: "CNY",
  is_mock: false,
  data_from: "2025-08-04",
  data_to: "2026-08-01",
  baseline_at: "2025-08-04",
  baseline_price: 3560,
  latest_close: 3625,
  previous_trading_day_return: -0.0116,
  values: [0, 0.018, -0.0116],
  cumulative_return: 0.0183,
  max_drawdown: -0.1128,
  max_drawdown_peak_at: "2026-05-13",
  max_drawdown_trough_at: "2026-07-17",
  coverage_ratio: 0.99,
  warnings: [],
} satisfies ComparisonSeries;

const quote = {
  symbol: "000001.SH",
  name: "上证指数",
  last_price: 3635.12,
  previous_close: 3625,
  change: 10.12,
  change_percent: 0.002791,
  open: 3621,
  high: 3640,
  low: 3618,
  volume: 521_000_000,
  quote_at: "2026-08-02T15:00:00+08:00",
  received_at: "2026-08-02T15:00:01+08:00",
  source: "sina-undocumented-quote",
  status: "CLOSED",
  is_stale: false,
} satisfies QuoteSnapshot;


describe("IndexPerformanceCard", () => {
  it("keeps historical closes distinct from the independent current quote", () => {
    const quoteState = { status: "READY", quote, error: null } satisfies ComparisonQuoteState;
    const markup = renderToStaticMarkup(
      <IndexPerformanceCard
        instrument={instrument}
        series={series}
        failure={null}
        quoteState={quoteState}
      />,
    );

    expect(markup).toContain("上证指数");
    expect(markup).toContain("000001.SH");
    expect(markup).toContain("起始价");
    expect(markup).toContain("¥3,560.00");
    expect(markup).toContain("区间末收盘");
    expect(markup).toContain("¥3,625.00");
    expect(markup).toContain("当前行情");
    expect(markup).toContain("¥3,635.12");
    expect(markup).toContain("当日涨跌");
    expect(markup).toContain("+0.28%");
    expect(markup).toContain("上一交易日");
    expect(markup).toContain("-1.16%");
    expect(markup).toContain("累计收益");
    expect(markup).toContain("+1.83%");
    expect(markup).toContain("最大回撤");
    expect(markup).toContain("-11.28%");
    expect(markup).toContain("2026-05-13 → 2026-07-17");
    expect(markup).toContain("历史日 K 与独立行情分开计算");
    expect(markup).not.toContain("市盈率");
  });

  it("shows quote data even when the historical series fails", () => {
    const quoteState = { status: "READY", quote, error: null } satisfies ComparisonQuoteState;
    const markup = renderToStaticMarkup(
      <IndexPerformanceCard
        instrument={instrument}
        series={null}
        failure={{ symbol: instrument.symbol, code: "UPSTREAM", message: "历史日 K 不可用" }}
        quoteState={quoteState}
      />,
    );

    expect(markup).toContain("历史日 K 不可用");
    expect(markup).toContain("¥3,635.12");
    expect(markup).toContain("当日涨跌");
    expect(markup).toContain("--");
  });
});
