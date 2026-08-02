import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { MarketBreadthSnapshot } from "../types/marketBreadth";
import { MarketBreadthPanel } from "./MarketBreadthPanel";


const binRows = [
  ["lt_m7", "<-7%", "DECLINE", 0],
  ["m7_m5", "-7%~-5%", "DECLINE", 0],
  ["m5_m3", "-5%~-3%", "DECLINE", 0],
  ["m3_m2", "-3%~-2%", "DECLINE", 0],
  ["m2_m1", "-2%~-1%", "DECLINE", 0],
  ["m1_0", "-1%~0", "DECLINE", 1],
  ["p0_p1", "0~1%", "ADVANCE", 0],
  ["p1_p2", "1%~2%", "ADVANCE", 0],
  ["p2_p3", "2%~3%", "ADVANCE", 0],
  ["p3_p5", "3%~5%", "ADVANCE", 0],
  ["p5_p7", "5%~7%", "ADVANCE", 0],
  ["gt_p7", ">7%", "ADVANCE", 1],
] as const;
const bins: MarketBreadthSnapshot["bins"] = binRows.map(
  ([id, label, side, count]) => ({ id, label, side, count }),
);


const snapshot = {
  status: "COMPLETE",
  market: "CN_A_SH_SZ_V1",
  mode: "OBSERVED",
  session_date: "2026-07-31",
  universe_id: "official-sh-sz-test-2026-07-31",
  universe_as_of: "2026-07-31",
  snapshot_at: "2026-08-01T16:05:00+08:00",
  received_at: "2026-08-02T07:00:00+00:00",
  source: "authorized-test-export",
  dataset_id: "sha256:test",
  quality_policy_version: "market-breadth-quality-v0.1",
  calculation_policy_version: "market-breadth-calculation-v0.1",
  universe_total: 4,
  covered: 3,
  unavailable: 1,
  explicitly_unavailable: 1,
  coverage_ratio: 0.75,
  resolution_ratio: 1,
  advancers: 1,
  decliners: 1,
  unchanged: 1,
  bins,
  unavailable_reasons: { SUSPENDED: 1 },
  issues: [],
} satisfies MarketBreadthSnapshot;


describe("MarketBreadthPanel", () => {
  it("renders backend-owned totals, bins, coverage and audit identity", () => {
    const markup = renderToStaticMarkup(
      <MarketBreadthPanel snapshot={snapshot} isLoading={false} error={null} onRefresh={() => {}} />,
    );

    expect(markup).toContain("沪深 A 股市场温度");
    expect(markup).toContain("新浪远端观测");
    expect(markup).toContain("涨 1");
    expect(markup).toContain("跌 1");
    expect(markup).toContain("平 1");
    expect(markup).toContain("不可用 1");
    expect(markup).toContain("覆盖 75.00%");
    expect(markup).toContain("交易日 2026-07-31");
    expect(markup).toContain("universe 2026-07-31");
    expect(markup).toContain("authorized-test-export");
    expect(markup).toContain("&lt;-7%");
    expect(markup).toContain("&gt;7%");
    expect(markup).toContain('data-testid="market-breadth-chart"');
  });


  it("does not render a distribution when quality status is failed", () => {
    const markup = renderToStaticMarkup(
      <MarketBreadthPanel
        snapshot={{
          ...snapshot,
          status: "FAILED",
          issues: [{
            code: "INSUFFICIENT_RESOLUTION",
            severity: "DANGER",
            message: "行情可解释比例低于 99.5% 门槛。",
          }],
        }}
        isLoading={false}
        error={null}
        onRefresh={() => {}}
      />,
    );

    expect(markup).toContain("数据质量未通过");
    expect(markup).toContain("行情可解释比例低于 99.5% 门槛。");
    expect(markup).not.toContain('data-testid="market-breadth-chart"');
  });


  it("renders backend provenance warnings without hiding an accepted distribution", () => {
    const markup = renderToStaticMarkup(
      <MarketBreadthPanel
        snapshot={{
          ...snapshot,
          source: "sina-undocumented-eod-import",
          issues: [{
            code: "SINA_UNDOCUMENTED_SOURCE",
            severity: "WARNING",
            message: "行情来自未文档化新浪网页端点。",
          }],
        }}
        isLoading={false}
        error={null}
        onRefresh={() => {}}
      />,
    );

    expect(markup).toContain("行情来自未文档化新浪网页端点。");
    expect(markup).toContain('data-testid="market-breadth-chart"');
  });


  it("shows a remote rejection without stale values", () => {
    const markup = renderToStaticMarkup(
      <MarketBreadthPanel
        snapshot={null}
        isLoading={false}
        error="市场温度不可用（HTTP 502）：新浪远端读取失败"
        onRefresh={() => {}}
      />,
    );

    expect(markup).toContain("市场温度不可用（HTTP 502）：新浪远端读取失败");
    expect(markup).not.toContain('data-testid="market-breadth-chart"');
  });
});
