import { FormEvent, useEffect, useRef, useState } from "react";

import { fetchMarketComparison } from "../api/comparison";
import { formatPercent } from "../format";
import type { MarketComparison } from "../types/comparison";
import { ComparisonChart } from "./ComparisonChart";
import { InstrumentSearch } from "./InstrumentSearch";


function formatDateRange(start: string | null, end: string | null): string {
  return start && end ? `${start} — ${end}` : "没有可比较的共同日期区间";
}


export function ComparisonPage() {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [comparison, setComparison] = useState<MarketComparison | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const requestRef = useRef<AbortController | null>(null);

  useEffect(() => () => requestRef.current?.abort(), []);

  const invalidateResult = () => {
    requestRef.current?.abort();
    requestRef.current = null;
    setComparison(null);
    setIsLoading(false);
  };

  const addSymbol = (symbol: string) => {
    setError(null);
    if (symbols.includes(symbol)) return;
    if (symbols.length >= 5) {
      setError("一次最多比较 5 个标的");
      return;
    }
    invalidateResult();
    setSymbols([...symbols, symbol]);
  };

  const removeSymbol = (symbol: string) => {
    invalidateResult();
    setSymbols((current) => current.filter((item) => item !== symbol));
    setError(null);
  };

  const changeStart = (value: string) => {
    invalidateResult();
    setStart(value);
    setError(null);
  };

  const changeEnd = (value: string) => {
    invalidateResult();
    setEnd(value);
    setError(null);
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (symbols.length < 2) {
      setError("请先选择至少 2 个标的");
      return;
    }
    if (start && end && start > end) {
      setError("开始日期不能晚于结束日期");
      return;
    }

    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    setIsLoading(true);
    setComparison(null);
    setError(null);
    fetchMarketComparison(
      symbols,
      { start: start || undefined, end: end || undefined },
      controller.signal,
    )
      .then(setComparison)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setComparison(null);
        setError(reason instanceof Error ? reason.message : "读取走势对比失败");
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false);
      });
  };

  return (
    <main className="comparison-shell">
      <section className="comparison-hero">
        <div>
          <p className="eyebrow">MULTI-INSTRUMENT RESEARCH</p>
          <h1>多标的日 K 走势对比</h1>
          <p>在共同覆盖区间内对齐交易日，以首个有效收盘价为基准比较累计收益与最大回撤。</p>
        </div>
        <aside>
          <strong>研究边界</strong>
          <span>不填充缺失日 · 不连接券商 · 不构成交易建议</span>
        </aside>
      </section>

      <form className="comparison-controls" onSubmit={submit}>
        <div className="comparison-controls__search">
          <label>添加标的（2–5 个）</label>
          <InstrumentSearch onSelect={addSymbol} variant="compact" actionLabel="添加" />
        </div>
        <label>
          开始日期
          <input type="date" value={start} onChange={(event) => changeStart(event.target.value)} />
        </label>
        <label>
          结束日期
          <input type="date" value={end} onChange={(event) => changeEnd(event.target.value)} />
        </label>
        <button type="submit" disabled={isLoading || symbols.length < 2}>
          {isLoading ? "计算中" : "开始对比"}
        </button>
      </form>

      <div className="comparison-symbols" aria-label="已选择标的">
        {symbols.length === 0 && <span className="comparison-symbols__empty">尚未选择标的</span>}
        {symbols.map((symbol) => (
          <button type="button" key={symbol} onClick={() => removeSymbol(symbol)}>
            {symbol}<span aria-hidden="true">×</span>
          </button>
        ))}
      </div>

      {error && <div className="comparison-message comparison-message--error">{error}</div>}
      {isLoading && <div className="comparison-message">正在读取并对齐历史日 K…</div>}

      {comparison && (
        <>
          <section className="comparison-summary">
            <div>
              <span>结果状态</span>
              <strong>{comparison.status === "COMPLETE" ? "完整" : comparison.status === "PARTIAL" ? "部分完成" : "失败"}</strong>
            </div>
            <div>
              <span>成功 / 失败</span>
              <strong>{comparison.succeeded} / {comparison.failed}</strong>
            </div>
            <div>
              <span>共同覆盖区间</span>
              <strong>{formatDateRange(comparison.common_from, comparison.common_to)}</strong>
            </div>
            <div>
              <span>统一日期点</span>
              <strong>{comparison.dates.length}</strong>
            </div>
          </section>

          {comparison.series.length > 0 && (
            <section className="comparison-chart-panel">
              <div className="comparison-section-heading">
                <div>
                  <p className="eyebrow">NORMALIZED RETURN</p>
                  <h2>归一化收益曲线</h2>
                </div>
                <span>缺失交易日保留为空，不以前值填充</span>
              </div>
              <ComparisonChart comparison={comparison} />
            </section>
          )}

          <section className="comparison-metrics" aria-label="多标的比较指标">
            {comparison.series.map((series) => (
              <article key={series.instrument.symbol}>
                <header>
                  <div>
                    <strong>{series.instrument.name}</strong>
                    <span>{series.instrument.symbol}</span>
                  </div>
                  <small>{series.adjustment}</small>
                </header>
                <dl>
                  <div><dt>累计收益</dt><dd>{formatPercent(series.cumulative_return, 2)}</dd></div>
                  <div><dt>最大回撤</dt><dd>{formatPercent(series.max_drawdown, 2)}</dd></div>
                  <div><dt>有效覆盖</dt><dd>{formatPercent(series.coverage_ratio, 1)}</dd></div>
                  <div><dt>基准日期</dt><dd>{series.baseline_at}</dd></div>
                </dl>
                <p>
                  回撤区间：{series.max_drawdown_peak_at && series.max_drawdown_trough_at
                    ? `${series.max_drawdown_peak_at} → ${series.max_drawdown_trough_at}`
                    : "区间内未出现收盘价回撤"}
                </p>
                <p>来源：{series.data_source} · 币种：{series.currency}</p>
                {series.warnings.map((warning) => (
                  <p className="comparison-metrics__warning" key={warning.code}>
                    {warning.message}
                  </p>
                ))}
              </article>
            ))}
          </section>

          {comparison.failures.length > 0 && (
            <section className="comparison-failures">
              <h2>未纳入比较的标的</h2>
              {comparison.failures.map((failure) => (
                <p key={`${failure.symbol}-${failure.code}`}>
                  <strong>{failure.symbol}</strong>
                  <span>[{failure.code}] {failure.message}</span>
                </p>
              ))}
            </section>
          )}
        </>
      )}
    </main>
  );
}
