import { useEffect, useRef, useState } from "react";

import { fetchMarketComparison } from "../api/comparison";
import { createComparisonRequestRunner } from "../comparisonRequest";
import { HOME_MARKET_INSTRUMENTS } from "../homeMarket";
import {
  dateRangeForPreset,
  INDEX_RANGE_PRESETS,
  type IndexRangePreset,
  validateIndexDateRange,
} from "../indexPerformance";
import type { ComparisonQuoteState } from "../comparisonQuotePolling";
import type { ComparisonFailure, MarketComparison } from "../types/comparison";
import { useComparisonQuotes } from "../useComparisonQuotes";
import { IndexPerformanceCard } from "./IndexPerformanceCard";


const INDEX_SYMBOLS = HOME_MARKET_INSTRUMENTS.map((instrument) => instrument.symbol);


function statusLabel(status: MarketComparison["status"]): string {
  if (status === "COMPLETE") return "完整";
  if (status === "PARTIAL") return "部分完成";
  return "失败";
}


export function IndexPerformancePage() {
  const initialRange = useRef(dateRangeForPreset("1Y"));
  const [activePreset, setActivePreset] = useState<IndexRangePreset | "CUSTOM">("1Y");
  const [start, setStart] = useState(initialRange.current.start);
  const [end, setEnd] = useState(initialRange.current.end);
  const [appliedStart, setAppliedStart] = useState(initialRange.current.start);
  const [appliedEnd, setAppliedEnd] = useState(initialRange.current.end);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [comparison, setComparison] = useState<MarketComparison | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const requestRunnerRef = useRef<ReturnType<typeof createComparisonRequestRunner> | null>(null);
  const quoteStates = useComparisonQuotes(INDEX_SYMBOLS);

  if (requestRunnerRef.current === null) {
    requestRunnerRef.current = createComparisonRequestRunner(fetchMarketComparison);
  }

  useEffect(() => {
    const runner = requestRunnerRef.current;
    if (!runner) return undefined;
    setIsLoading(true);
    setComparison(null);
    setRequestError(null);
    runner.run(
      INDEX_SYMBOLS,
      { start: appliedStart, end: appliedEnd },
      {
        success: setComparison,
        failure: (reason: unknown) => {
          setRequestError(reason instanceof Error ? reason.message : "读取指数表现失败");
        },
        settled: () => setIsLoading(false),
      },
    );
    return () => runner.invalidate();
  }, [appliedEnd, appliedStart, refreshVersion]);

  const applyPreset = (preset: IndexRangePreset) => {
    const range = dateRangeForPreset(preset);
    setValidationError(null);
    setActivePreset(preset);
    setStart(range.start);
    setEnd(range.end);
    setAppliedStart(range.start);
    setAppliedEnd(range.end);
    setRefreshVersion((version) => version + 1);
  };

  const applyCustomRange = () => {
    const issue = validateIndexDateRange(start, end);
    if (issue) {
      setValidationError(issue);
      return;
    }
    setValidationError(null);
    setActivePreset("CUSTOM");
    setAppliedStart(start);
    setAppliedEnd(end);
    setRefreshVersion((version) => version + 1);
  };

  const seriesBySymbol = new Map(
    comparison?.series.map((series) => [series.instrument.symbol, series]) ?? [],
  );
  const failureBySymbol = new Map(
    comparison?.failures.map((failure) => [failure.symbol, failure]) ?? [],
  );

  return (
    <main className="index-performance-shell">
      <section className="index-performance-hero">
        <div>
          <p className="eyebrow">INDEX PERFORMANCE · DAILY RESEARCH</p>
          <h1>主要指数区间表现</h1>
          <p>
            用同一日期区间查看 8 个沪深宽基指数的历史收益、最大回撤与独立行情快照。
          </p>
        </div>
        <aside>
          <strong>计算边界</strong>
          <span>历史指标由后端计算；盘中行情不参与累计收益与最大回撤。</span>
        </aside>
      </section>

      <section className="index-performance-controls" aria-label="指数表现日期区间">
        <h2 className="sr-only">自定义区间与快捷范围</h2>
        <div className="index-performance-presets" aria-label="快捷日期区间">
          {INDEX_RANGE_PRESETS.map((preset) => (
            <button
              type="button"
              className={activePreset === preset.value ? "is-active" : ""}
              aria-pressed={activePreset === preset.value}
              onClick={() => applyPreset(preset.value)}
              key={preset.value}
            >
              {preset.label}
            </button>
          ))}
        </div>
        <div className="index-performance-custom-range">
          <label>
            开始日期
            <input
              type="date"
              value={start}
              onChange={(event) => {
                setStart(event.target.value);
                setActivePreset("CUSTOM");
                setValidationError(null);
              }}
            />
          </label>
          <label>
            结束日期
            <input
              type="date"
              value={end}
              onChange={(event) => {
                setEnd(event.target.value);
                setActivePreset("CUSTOM");
                setValidationError(null);
              }}
            />
          </label>
          <button type="button" onClick={applyCustomRange}>应用区间</button>
          <button
            type="button"
            className="index-performance-refresh"
            onClick={() => setRefreshVersion((version) => version + 1)}
            disabled={isLoading}
          >
            {isLoading ? "刷新中" : "刷新"}
          </button>
        </div>
      </section>

      <section className="index-performance-summary" aria-live="polite">
        <div>
          <span>请求区间</span>
          <strong>{appliedStart} → {appliedEnd}</strong>
        </div>
        <div>
          <span>历史结果</span>
          <strong>{isLoading ? "读取中" : comparison ? statusLabel(comparison.status) : "不可用"}</strong>
        </div>
        <div>
          <span>成功 / 失败</span>
          <strong>{comparison ? `${comparison.succeeded} / ${comparison.failed}` : "--"}</strong>
        </div>
        <div>
          <span>共同覆盖区间</span>
          <strong>{comparison?.common_from && comparison.common_to
            ? `${comparison.common_from} → ${comparison.common_to}`
            : "--"}</strong>
        </div>
      </section>

      {validationError && (
        <div className="index-performance-message index-performance-message--error">
          {validationError}
        </div>
      )}
      {requestError && (
        <div className="index-performance-message index-performance-message--error">
          {requestError}
        </div>
      )}
      {comparison?.status === "PARTIAL" && (
        <div className="index-performance-message">
          部分指数历史序列不可用；已保留成功结果，并继续独立读取每个指数的行情快照。
        </div>
      )}

      <section className="index-performance-grid" aria-label="主要指数区间表现卡片">
        {HOME_MARKET_INSTRUMENTS.map((instrument) => {
          const requestFailure: ComparisonFailure | null = requestError
            ? { symbol: instrument.symbol, code: "REQUEST_FAILED", message: requestError }
            : null;
          const quoteState: ComparisonQuoteState = quoteStates[instrument.symbol] ?? {
            status: "LOADING",
            quote: null,
            error: null,
          };
          return (
            <IndexPerformanceCard
              instrument={instrument}
              series={seriesBySymbol.get(instrument.symbol) ?? null}
              failure={failureBySymbol.get(instrument.symbol) ?? requestFailure}
              quoteState={quoteState}
              key={instrument.symbol}
            />
          );
        })}
      </section>

      <footer className="index-performance-boundary">
        <strong>数据边界</strong>
        <span>
          历史日 K 与行情均来自新浪未文档化接口；复权、指数估值和交易级时效均未获得正式合同保证。本页仅供研究与审计，不构成交易建议。
        </span>
      </footer>
    </main>
  );
}
