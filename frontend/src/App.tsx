import { useCallback, useEffect, useState } from "react";

import { fetchDashboard } from "./api/dashboard";
import { fetchQuote } from "./api/quote";
import { ChanChart } from "./components/ChanChart";
import { ComparisonPage } from "./components/ComparisonPage";
import { DataQualityPanel } from "./components/DataQualityPanel";
import { HomePage } from "./components/HomePage";
import { InstrumentSearch, normalizeDirectSymbol } from "./components/InstrumentSearch";
import { MetricCard } from "./components/MetricCard";
import { PerformanceCard } from "./components/PerformanceCard";
import { QuotePanel } from "./components/QuotePanel";
import { SiteHeader } from "./components/SiteHeader";
import { startQuotePolling } from "./quotePolling";
import type { DashboardSnapshot } from "./types/dashboard";
import type { QuoteSnapshot } from "./types/quote";


export function symbolFromSearch(search: string): string | null {
  const requested = new URLSearchParams(search).get("symbol");
  return requested ? normalizeDirectSymbol(requested) : null;
}


export type AppView =
  | { name: "home" }
  | { name: "search" }
  | { name: "comparison" }
  | { name: "dashboard"; symbol: string };


export function appViewFromLocation(pathname: string, search: string): AppView {
  const symbol = symbolFromSearch(search);
  if (symbol) {
    return { name: "dashboard", symbol };
  }
  const normalizedPath = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  if (normalizedPath === "/compare") {
    return { name: "comparison" };
  }
  return normalizedPath === "/search" ? { name: "search" } : { name: "home" };
}


function LandingPage({ onSelect }: { onSelect: (symbol: string) => void }) {
  return (
    <main className="landing-page">
      <section className="landing-card">
        <div className="landing-card__mark" aria-hidden="true">CQ</div>
        <p className="eyebrow">CHAN QUANT · 缠论量化研究台</p>
        <h1>从一个标的开始结构研究</h1>
        <p className="landing-card__intro">
          搜索沪深股票、ETF 或指数的代码与名称，查看可追溯的趋势状态、结构事件与研究证据。
        </p>
        <InstrumentSearch onSelect={(instrument) => onSelect(instrument.symbol)} />
        <div className="landing-card__examples" aria-label="搜索示例">
          <span>股票：600519.SH</span>
          <span>ETF：513100.SH</span>
          <span>名称：纳指ETF国泰</span>
        </div>
        <p className="landing-card__boundary">
          研究与审计工具 · Independent v0.1 草案 · 不构成交易建议
        </p>
      </section>
    </main>
  );
}


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
  const displayedName = instrument.name;

  return (
    <main className="dashboard-shell">
      <div className="workspace-heading">
        <h1>{displayedName}</h1>
        <div className="toolbar__meta">
          <span>{instrument.symbol}</span>
          <span>日线</span>
          <span>截至 {instrument.as_of}</span>
          <span>{instrument.data_source}</span>
          <span>复权：{instrument.adjustment}</span>
          <span>{snapshot.strategy.version}</span>
        </div>
      </div>

      {snapshot.is_mock && (
        <div className="mock-banner">
          合成行情 · Independent v0.1 草案规则实时计算 · 不代表真实行情、回测或交易建议
        </div>
      )}
      {!snapshot.is_mock && snapshot.strategy.rule_status === "DRAFT" && (
        <div className="mock-banner">
          {instrument.data_source === "sina-undocumented-kline"
            ? instrument.asset_type === "ETF"
              ? "新浪财经未文档化 ETF 日 K · 复权、分红与份额折算口径未验证 · 不代表交易建议"
              : instrument.adjustment === "unadjusted-observed"
                ? "新浪财经匿名 K 线端点 · 有限股票样本现场观测为不复权 · 无固定口径合同或 SLA · 不代表交易建议"
                : "新浪财经匿名 K 线端点 · 标的元数据与复权口径未经确认 · 不代表交易建议"
            : instrument.data_source === "auditable-market-snapshot"
              ? "本地历史行情快照 · SHA-256 与结构合同已检查 · Independent v0.1 仍是待验证草案 · 不代表交易建议"
              : "外部 CSV 行情 · Independent v0.1 仍是待验证草案 · 不代表交易建议"}
        </div>
      )}

      {snapshot.data_quality && <DataQualityPanel report={snapshot.data_quality} />}

      <QuotePanel
        symbol={instrument.symbol}
        instrumentName={instrument.name}
        pricePrecision={instrument.price_precision}
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
        <ChanChart chart={snapshot.chart} pricePrecision={instrument.price_precision} />
      </section>
    </main>
  );
}


function ResearchWorkspace({
  symbol,
}: {
  symbol: string;
}) {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [quote, setQuote] = useState<QuoteSnapshot | null>(null);
  const [quoteError, setQuoteError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchDashboard(symbol, controller.signal)
      .then(setSnapshot)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") {
          return;
        }
        setError(reason instanceof Error ? reason.message : "读取策略快照失败");
      });
    return () => controller.abort();
  }, [symbol]);

  useEffect(() => startQuotePolling({
    symbol,
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
  }), [symbol]);

  if (error || !snapshot) {
    return (
      <main className="dashboard-shell">
        <div className="workspace-heading">
          <h1>{symbol}</h1>
        </div>
        <div className={`page-state page-state--within${error ? " page-state--error" : ""}`}>
          {error ?? `正在读取 ${symbol} 的策略快照…`}
        </div>
      </main>
    );
  }

  return (
    <Dashboard
      snapshot={snapshot}
      quote={quote}
      quoteError={quoteError}
    />
  );
}


export default function App() {
  const [view, setView] = useState<AppView>(() => (
    appViewFromLocation(window.location.pathname, window.location.search)
  ));

  useEffect(() => {
    const handlePopState = () => setView(
      appViewFromLocation(window.location.pathname, window.location.search),
    );
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigateToSymbol = useCallback((nextSymbol: string) => {
    const normalized = normalizeDirectSymbol(nextSymbol);
    if (!normalized) {
      return;
    }
    const url = new URL(window.location.href);
    url.pathname = "/";
    url.search = "";
    url.searchParams.set("symbol", normalized);
    window.history.pushState({}, "", url);
    setView({ name: "dashboard", symbol: normalized });
  }, []);

  const navigateHome = useCallback(() => {
    const url = new URL(window.location.href);
    url.pathname = "/";
    url.search = "";
    window.history.pushState({}, "", url);
    setView({ name: "home" });
  }, []);

  const navigateResearch = useCallback(() => {
    const url = new URL(window.location.href);
    url.pathname = "/search";
    url.search = "";
    window.history.pushState({}, "", url);
    setView({ name: "search" });
  }, []);

  const navigateComparison = useCallback(() => {
    const url = new URL(window.location.href);
    url.pathname = "/compare";
    url.search = "";
    window.history.pushState({}, "", url);
    setView({ name: "comparison" });
  }, []);

  return (
    <>
      <SiteHeader
        activeSection={view.name === "home" ? "market" : view.name === "comparison" ? "comparison" : "research"}
        onNavigateHome={navigateHome}
        onNavigateComparison={navigateComparison}
        onNavigateResearch={navigateResearch}
        onSelect={navigateToSymbol}
      />
      {view.name === "home" && <HomePage onNavigateComparison={navigateComparison} />}
      {view.name === "search" && <LandingPage onSelect={navigateToSymbol} />}
      {view.name === "comparison" && <ComparisonPage />}
      {view.name === "dashboard" && (
        <ResearchWorkspace key={view.symbol} symbol={view.symbol} />
      )}
    </>
  );
}
