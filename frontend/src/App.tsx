import { useEffect, useState } from "react";

import { fetchDashboard } from "./api/dashboard";
import { fetchQuote } from "./api/quote";
import { ChanChart } from "./components/ChanChart";
import { MetricCard } from "./components/MetricCard";
import { PerformanceCard } from "./components/PerformanceCard";
import { QuotePanel } from "./components/QuotePanel";
import { startQuotePolling } from "./quotePolling";
import type { DashboardSnapshot } from "./types/dashboard";
import type { QuoteSnapshot } from "./types/quote";

const requestedSymbol = new URLSearchParams(window.location.search).get("symbol");
const SYMBOL = requestedSymbol?.trim().toUpperCase() || "DEMO.SZ";

function Dashboard({
  snapshot,
  quote,
  quoteError,
}: {
  snapshot: DashboardSnapshot;
  quote: QuoteSnapshot | null;
  quoteError: string | null;
}) {
  const { instrument, recommendation, signal_performance: performance } = snapshot;

  return (
    <main className="dashboard-shell">
      <header className="toolbar">
        <div>
          <p className="eyebrow">CHAN QUANT · 缠论量化研究台</p>
          <h1>{instrument.name}</h1>
        </div>
        <div className="toolbar__meta">
          <span>{instrument.symbol}</span>
          <span>日线</span>
          <span>截至 {instrument.as_of}</span>
          <span>{instrument.data_source}</span>
          <span>复权：{instrument.adjustment}</span>
          <span>{snapshot.strategy.version}</span>
        </div>
      </header>

      {snapshot.is_mock && (
        <div className="mock-banner">
          合成行情 · Independent v0.1 草案规则实时计算 · 不代表真实行情、回测或交易建议
        </div>
      )}
      {!snapshot.is_mock && snapshot.strategy.rule_status === "DRAFT" && (
        <div className="mock-banner">
          {instrument.data_source === "sina-undocumented-kline"
            ? "新浪财经匿名 K 线端点 · 现场观测为不复权 · 无固定口径合同或 SLA · 不代表交易建议"
            : "外部 CSV 行情 · Independent v0.1 仍是待验证草案 · 不代表交易建议"}
        </div>
      )}

      <QuotePanel
        symbol={instrument.symbol}
        strategyAsOf={instrument.as_of}
        quote={quote}
        error={quoteError}
      />

      <section className="status-chips" aria-label="策略状态">
        {snapshot.status_chips.map((chip) => (
          <span className={`status-chip status-chip--${chip.tone}`} key={chip.label}>
            {chip.label}
          </span>
        ))}
      </section>

      <section className="metric-grid" aria-label="核心策略指标">
        {snapshot.metrics.map((metric) => (
          <MetricCard key={metric.key} metric={metric} />
        ))}
      </section>

      <section className="recommendation-panel">
        <h2>▢ 操作建议</h2>
        <strong className="recommendation-panel__title">{recommendation.title}</strong>
        {recommendation.filter_reasons.map((reason) => (
          <p key={reason.code}>过滤原因：{reason.message}</p>
        ))}
        {recommendation.evidence_lines.map((line) => (
          <p key={line}>{line}</p>
        ))}
        {recommendation.warnings.map((warning) => (
          <p className="recommendation-panel__warning" key={warning.type}>
            风险提示：🟠 {warning.message}
          </p>
        ))}
        <p className="recommendation-panel__mock">{recommendation.summary}</p>
      </section>

      <section className="performance-section">
        <h2>〽 买卖点历史成功率 · 近 {performance.lookback_years} 年 · {performance.headline_total} 个信号</h2>
        <p className="section-note">
          草案事件研究：买点统计后续上涨，退出点统计后续下跌；含 {performance.excluded_total} 个排除项
        </p>
        <div className="performance-grid">
          <PerformanceCard performance={performance.buy} />
          <PerformanceCard performance={performance.sell} />
        </div>
      </section>

      <section className="chart-section">
        <h2>▥ 缠论 K 线 · 买卖点 · 策略线</h2>
        <ChanChart chart={snapshot.chart} />
      </section>
    </main>
  );
}

export default function App() {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [quote, setQuote] = useState<QuoteSnapshot | null>(null);
  const [quoteError, setQuoteError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboard(SYMBOL).then(setSnapshot).catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : "读取策略快照失败");
    });
  }, []);

  useEffect(() => startQuotePolling({
    symbol: SYMBOL,
    fetchQuote,
    onQuote: (nextQuote) => {
      setQuote(nextQuote);
      setQuoteError(null);
    },
    onError: (reason) => {
      setQuote(null);
      setQuoteError(reason instanceof Error ? reason.message : "实时行情不可用");
    },
    visibilitySource: document,
    intervalMs: 8_000,
  }), []);

  if (error) {
    return <div className="page-state page-state--error">{error}</div>;
  }
  if (!snapshot) {
    return <div className="page-state">正在读取 mock 策略快照…</div>;
  }
  return <Dashboard snapshot={snapshot} quote={quote} quoteError={quoteError} />;
}
