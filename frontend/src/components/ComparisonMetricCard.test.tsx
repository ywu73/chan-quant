import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { ComparisonQuoteState } from "../comparisonQuotePolling";
import type { ComparisonSeries } from "../types/comparison";
import type { QuoteSnapshot } from "../types/quote";
import { ComparisonMetricCard } from "./ComparisonMetricCard";


const series = {
  instrument: {
    symbol: "000001.SZ",
    name: "平安银行",
    exchange: "SZ",
    asset_type: "UNKNOWN",
    price_precision: 2,
  },
  data_source: "sina-undocumented-kline",
  adjustment: "unadjusted-observed",
  currency: "CNY",
  is_mock: false,
  data_from: "2026-01-01",
  data_to: "2026-01-03",
  baseline_at: "2026-01-01",
  baseline_price: 100,
  latest_close: 88,
  previous_trading_day_return: 0.1,
  values: [0, 0.1, -0.12],
  cumulative_return: -0.12,
  max_drawdown: -0.2,
  max_drawdown_peak_at: "2026-01-02",
  max_drawdown_trough_at: "2026-01-03",
  coverage_ratio: 1,
  warnings: [],
} satisfies ComparisonSeries;

const quote = {
  symbol: "000001.SZ",
  name: "平安银行",
  last_price: 11.62,
  previous_close: 11.48,
  change: 0.14,
  change_percent: 0.012195,
  open: 11.48,
  high: 11.67,
  low: 11.42,
  volume: 63_210_000,
  quote_at: "2026-08-01T14:35:06+08:00",
  received_at: "2026-08-01T14:35:07+08:00",
  source: "sina-undocumented-quote",
  status: "LIVE",
  is_stale: false,
} satisfies QuoteSnapshot;


describe("ComparisonMetricCard", () => {
  it("shows historical metrics beside a separately labelled quote snapshot", () => {
    const quoteState = {
      status: "READY",
      quote,
      error: null,
    } satisfies ComparisonQuoteState;

    const markup = renderToStaticMarkup(
      <ComparisonMetricCard series={series} quoteState={quoteState} />,
    );

    expect(markup).toContain("起始价");
    expect(markup).toContain("¥100.00");
    expect(markup).toContain("区间末收盘");
    expect(markup).toContain("¥88.00");
    expect(markup).toContain("上一交易日");
    expect(markup).toContain("10.00%");
    expect(markup).toContain("历史比较指标");
    expect(markup).toContain("独立行情快照");
    expect(markup).toContain("实时");
    expect(markup).toContain("最新价");
    expect(markup).toContain("¥11.62");
    expect(markup).toContain("涨跌额");
    expect(markup).toContain("+¥0.14");
    expect(markup).toContain("涨跌幅");
    expect(markup).toContain("1.22%");
    expect(markup).toContain("昨收");
    expect(markup).toContain("¥11.48");
    expect(markup).toContain("今开");
    expect(markup).toContain("最高");
    expect(markup).toContain("¥11.67");
    expect(markup).toContain("最低");
    expect(markup).toContain("¥11.42");
    expect(markup).toContain("成交量");
    expect(markup).toContain("6321.00 万");
    expect(markup).toContain("行情时间 2026-08-01 14:35:06");
    expect(markup).toContain("接收时间 2026-08-01 14:35:07");
    expect(markup).toContain("sina-undocumented-quote");
    expect(markup).toContain("盘中价不参与历史比较指标计算");
  });

  it("uses the instrument precision for every quote price", () => {
    const etfSeries = {
      ...series,
      instrument: {
        symbol: "513100.SH",
        name: "纳指ETF国泰",
        exchange: "SH",
        asset_type: "ETF",
        price_precision: 3,
      },
    } satisfies ComparisonSeries;
    const etfQuote = {
      ...quote,
      symbol: "513100.SH",
      name: "纳指ETF国泰",
      last_price: 2.112,
      previous_close: 2.1,
      change: 0.012,
      open: 2.101,
      high: 2.123,
      low: 2.098,
    } satisfies QuoteSnapshot;
    const quoteState = {
      status: "READY",
      quote: etfQuote,
      error: null,
    } satisfies ComparisonQuoteState;

    const markup = renderToStaticMarkup(
      <ComparisonMetricCard series={etfSeries} quoteState={quoteState} />,
    );

    expect(markup).toContain("¥2.112");
    expect(markup).toContain("+¥0.012");
    expect(markup).toContain("¥2.100");
    expect(markup).toContain("¥2.101");
    expect(markup).toContain("¥2.123");
    expect(markup).toContain("¥2.098");
  });

  it("shows delayed, closed, and stale quote lifecycle states", () => {
    const cases = [
      ["DELAYED", false, "延迟"],
      ["CLOSED", false, "已收盘"],
      ["LIVE", true, "已过期"],
    ] as const;

    for (const [status, isStale, label] of cases) {
      const quoteState = {
        status: "READY",
        quote: { ...quote, status, is_stale: isStale },
        error: null,
      } satisfies ComparisonQuoteState;
      const markup = renderToStaticMarkup(
        <ComparisonMetricCard series={series} quoteState={quoteState} />,
      );

      expect(markup).toContain(label);
    }
  });

  it("keeps historical metrics visible when the quote fails", () => {
    const quoteState = {
      status: "ERROR",
      quote: null,
      error: "实时行情不可用（HTTP 503）",
    } satisfies ComparisonQuoteState;

    const markup = renderToStaticMarkup(
      <ComparisonMetricCard series={series} quoteState={quoteState} />,
    );

    expect(markup).toContain("累计收益");
    expect(markup).toContain("-12.00%");
    expect(markup).toContain("实时行情不可用（HTTP 503）");
    expect(markup).not.toContain("最新价");
    expect(markup).not.toContain("成交量");
  });
});
