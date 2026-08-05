import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { PortfolioStudy } from "../types/dashboard";
import { PortfolioStudyPanel } from "./PortfolioStudyPanel";


const study = {
  methodology_status: "HYPOTHETICAL_RESEARCH_ASSUMPTIONS",
  policy: {
    version: "cn-a-fixed-10pct-v1",
    initial_cash: 100000,
    commission_bps: 3,
    minimum_commission: 5,
    sell_tax_bps: 5,
    slippage_bps: 5,
    lot_size: 100,
    max_position_fraction: 0.95,
    price_limit_ratio: 0.1,
    price_limit_decimals: 2,
  },
  market_constraints: [],
  statistics: {
    starting_cash: 100000,
    ending_equity: 110000,
    total_return: 0.1,
    max_drawdown: -0.05,
    filled_orders: 2,
    rejected_orders: 1,
    rejected_reasons: { PRICE_LIMIT_UP: 1 },
    closed_positions: 1,
    winning_positions: 1,
    win_rate: 1,
    total_costs: 25,
    slippage_cost: 10,
    turnover: 1.8,
    exposure_ratio: 0.4,
    open_position_quantity: 0,
    realized_pnl: 10000,
    unrealized_pnl: 0,
  },
  decisions: [],
  equity_curve: [],
  warnings: [
    {
      code: "FIXED_LIMIT_ASSUMPTION",
      message: "固定 10% 涨跌停是假设，不覆盖 ST、20%/30%、IPO、ETF 与指数差异。",
    },
  ],
} satisfies PortfolioStudy;


describe("PortfolioStudyPanel", () => {
  it("labels hypothetical results, costs, constraints, and rejection reasons", () => {
    const markup = renderToStaticMarkup(<PortfolioStudyPanel study={study} />);

    expect(markup).toContain("假设组合研究");
    expect(markup).toContain("不代表可实现交易绩效");
    expect(markup).toContain("总成本");
    expect(markup).toContain("涨跌停");
    expect(markup).toContain("PRICE_LIMIT_UP");
    expect(markup).toContain("固定 10% 涨跌停是假设");
  });
});
